import os
from importlib import import_module
import click
from .arguments import username, password, email, verbose
import sys


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
    env = os.getenv("FLASK_ENV", "development")
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        from cornflow import create_app
    else:
        sys.path.append("./")
        external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
        external_module = import_module(external_app)
        create_app = external_module.wsgi.create_app

    app = create_app(env)
    with app.app_context():
        from cornflow.commands import create_user_with_role
        from cornflow.shared.const import SERVICE_ROLE

        create_user_with_role(
            username, email, password, "service user", SERVICE_ROLE, verbose=verbose
        )
