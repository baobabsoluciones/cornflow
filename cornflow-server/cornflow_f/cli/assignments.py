"""
User-Role assignment commands
"""

import click
from cornflow_f.database import get_db
from cornflow_f.models.user import UserModel
from cornflow_f.models.role import RoleModel
from cornflow_f.models.user_role import UserRoleModel


@click.group()
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
