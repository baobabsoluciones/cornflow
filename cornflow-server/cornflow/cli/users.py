import click
from cornflow.cli.arguments import username, password, email, verbose
from cornflow.cli.utils import get_app
from cornflow.commands import create_user_with_role
from cornflow.shared.const import SERVICE_ROLE


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

        create_user_with_role(
            username, email, password, "service user", SERVICE_ROLE, verbose=verbose
        )
