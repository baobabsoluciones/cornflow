import os
from importlib import import_module
import click
from .arguments import username, password, email, verbose
import sys

from .utils import get_app


@click.group(name="users", help="Commands to manage the users")
def users():
    pass


@click.group(name="create", help="Create a user")
def create():
    pass


users.add_command(create)


@create.command(name="service", help="Create a service user")
@username
@password
@email
@verbose
def create_service_user(username, password, email, verbose):
    app = get_app()
    with app.app_context():
        from cornflow.commands import create_user_with_role
        from cornflow.shared.const import SERVICE_ROLE

        create_user_with_role(
            username, email, password, "service user", SERVICE_ROLE, verbose=verbose
        )
