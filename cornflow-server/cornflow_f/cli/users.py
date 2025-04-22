"""
User management commands
"""

import click
from cornflow_f.database import get_db
from cornflow_f.models.user import UserModel
from cornflow_f.security import get_password_hash


@click.group()
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
