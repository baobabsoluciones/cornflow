"""
Role management commands
"""

import click
from cornflow_f.database import get_db
from cornflow_f.models.role import RoleModel
from cornflow_f.shared.const import DEFAULT_ROLES


@click.group()
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
