"""
Command Line Interface for managing users and roles
"""

import click
from sqlalchemy.orm import Session
from cornflow_f.database import get_db
from cornflow_f.models.user import UserModel
from cornflow_f.models.role import RoleModel
from cornflow_f.models.user_role import UserRoleModel
from cornflow_f.security import get_password_hash
from cornflow_f.shared.const import DEFAULT_ROLES


@click.group()
def cli():
    """
    Cornflow CLI for managing users and roles
    """
    pass


@cli.group()
def users():
    """
    User management commands
    """
    pass


@users.command()
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
@click.option("--first-name", prompt=True)
@click.option("--last-name", prompt=True)
def create(username: str, email: str, password: str, first_name: str, last_name: str):
    """
    Create a new user
    """
    db = next(get_db())
    try:
        if UserModel.exists_by_username(db, username):
            click.echo("Error: Username already exists")
            return

        if UserModel.exists_by_email(db, email):
            click.echo("Error: Email already exists")
            return

        user = UserModel(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.save(db)
        click.echo(f"User {username} created successfully")
    except Exception as e:
        click.echo(f"Error creating user: {str(e)}")


@users.command()
@click.option("--username", prompt=True)
def delete(username: str):
    """
    Delete a user
    """
    db = next(get_db())
    try:
        user = UserModel.get_by_username(db, username)
        if not user:
            click.echo("Error: User not found")
            return

        user.delete(db)
        click.echo(f"User {username} deleted successfully")
    except Exception as e:
        click.echo(f"Error deleting user: {str(e)}")


@cli.group()
def roles():
    """
    Role management commands
    """
    pass


@roles.command()
@click.option("--name", prompt=True)
@click.option("--description", prompt=True)
def create(name: str, description: str):
    """
    Create a new role
    """
    db = next(get_db())
    try:
        if RoleModel.exists_by_name(db, name):
            click.echo("Error: Role already exists")
            return

        role = RoleModel(name=name, description=description)
        role.save(db)
        click.echo(f"Role {name} created successfully")
    except Exception as e:
        click.echo(f"Error creating role: {str(e)}")


@roles.command()
@click.option("--name", prompt=True)
def delete(name: str):
    """
    Delete a role
    """
    db = next(get_db())
    try:
        role = RoleModel.get_by_name(db, name)
        if not role:
            click.echo("Error: Role not found")
            return

        role.delete(db)
        click.echo(f"Role {name} deleted successfully")
    except Exception as e:
        click.echo(f"Error deleting role: {str(e)}")


@roles.command()
def list():
    """
    List all roles
    """
    db = next(get_db())
    try:
        roles = db.query(RoleModel).filter(RoleModel.deleted_at.is_(None)).all()
        if not roles:
            click.echo("No roles found")
            return

        click.echo("Available roles:")
        for role in roles:
            click.echo(f"- {role.name}: {role.description or 'No description'}")
    except Exception as e:
        click.echo(f"Error listing roles: {str(e)}")


@roles.command()
def init():
    """
    Initialize default roles
    """
    db = next(get_db())
    try:
        for role_data in DEFAULT_ROLES:
            if not RoleModel.exists_by_name(db, role_data["name"]):
                role = RoleModel(**role_data)
                role.save(db)
                click.echo(f"Created role: {role.name}")
            else:
                click.echo(f"Role already exists: {role_data['name']}")
        click.echo("Default roles initialized successfully")
    except Exception as e:
        click.echo(f"Error initializing default roles: {str(e)}")


@cli.group()
def assignments():
    """
    User-Role assignment commands
    """
    pass


@assignments.command()
@click.option("--username", prompt=True)
@click.option("--role", prompt=True)
def assign(username: str, role: str):
    """
    Assign a role to a user
    """
    db = next(get_db())
    try:
        user = UserModel.get_by_username(db, username)
        if not user:
            click.echo("Error: User not found")
            return

        role_obj = RoleModel.get_by_name(db, role)
        if not role_obj:
            click.echo("Error: Role not found")
            return

        if UserRoleModel.has_role(db, user.id, role_obj.id):
            click.echo("Error: User already has this role")
            return

        user_role = UserRoleModel(user_id=user.id, role_id=role_obj.id)
        user_role.save(db)
        click.echo(f"Role {role} assigned to user {username} successfully")
    except Exception as e:
        click.echo(f"Error assigning role: {str(e)}")


@assignments.command()
@click.option("--username", prompt=True)
@click.option("--role", prompt=True)
def remove(username: str, role: str):
    """
    Remove a role from a user
    """
    db = next(get_db())
    try:
        user = UserModel.get_by_username(db, username)
        if not user:
            click.echo("Error: User not found")
            return

        role_obj = RoleModel.get_by_name(db, role)
        if not role_obj:
            click.echo("Error: Role not found")
            return

        user_role = (
            db.query(UserRoleModel)
            .filter(
                UserRoleModel.user_id == user.id,
                UserRoleModel.role_id == role_obj.id,
                UserRoleModel.deleted_at.is_(None),
            )
            .first()
        )

        if not user_role:
            click.echo("Error: User does not have this role")
            return

        user_role.delete(db)
        click.echo(f"Role {role} removed from user {username} successfully")
    except Exception as e:
        click.echo(f"Error removing role: {str(e)}")


@assignments.command()
@click.option("--username", prompt=True)
def list(username: str):
    """
    List all roles assigned to a user
    """
    db = next(get_db())
    try:
        user = UserModel.get_by_username(db, username)
        if not user:
            click.echo("Error: User not found")
            return

        roles = user.get_roles(db)
        if not roles:
            click.echo(f"User {username} has no roles assigned")
            return

        click.echo(f"Roles for user {username}:")
        for user_role in roles:
            role = RoleModel.get_by_id(db, user_role.role_id)
            click.echo(f"- {role.name}: {role.description or 'No description'}")
    except Exception as e:
        click.echo(f"Error listing roles: {str(e)}")


if __name__ == "__main__":
    cli()
