import click

from cornflow.cli.arguments import username, password, email, verbose
from cornflow.cli.utils import get_app
from cornflow.commands import create_user_with_role
from cornflow.models import UserModel
from cornflow.shared.authentication.auth import BIAuth
from cornflow.shared.const import SERVICE_ROLE, VIEWER_ROLE
from cornflow.shared.exceptions import (
    ObjectDoesNotExist,
    NoPermission,
)


@click.group(name="users", help="Commands to manage the users")
def users():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@click.group(name="create", help="Create a user")
def create():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
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


@create.command(name="viewer", help="Create a viewer user")
@username
@password
@email
@verbose
def create_viewer_user(username, password, email, verbose):
    app = get_app()
    with app.app_context():
        create_user_with_role(
            username, email, password, "viewer user", VIEWER_ROLE, verbose=verbose
        )


@create.command(
    name="token",
    help="Creates a token for a user that is never going to expire. This token can only be used on BI endpoints",
)
@click.option(
    "--idx", "-i", type=int, help="The id of the user to generate the token for"
)
@username
@password
def create_unexpiring_token(idx, username, password):
    app = get_app()
    with app.app_context():
        user = UserModel.get_one_object(id=idx)
        asking_user = UserModel.get_one_user_by_username(username)

        if not asking_user.check_hash(password) or not asking_user.is_service_user():
            raise NoPermission("The asking user has no permissions to generate tokens")

        if not user:
            raise ObjectDoesNotExist("User does not exist")

        token = BIAuth.generate_token(idx)
        click.echo(token)
        return True
