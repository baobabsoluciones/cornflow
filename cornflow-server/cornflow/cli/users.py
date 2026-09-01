import click

from cornflow.cli.arguments import username, password, email, verbose
from cornflow.cli.utils import get_app
from cornflow.commands import create_user_with_role
from cornflow.models import UserModel
from cornflow.shared.audit import audit
from cornflow.shared.authentication.auth import BIAuth
from cornflow.shared.const import (
    API_KEY_SCOPE_FULL,
    API_KEY_SCOPE_READ,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_PLANNER_ROLE,
    PLATFORM_VIEWER_ROLE,
    SERVICE_ROLE,
    VIEWER_ROLE,
)
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


@create.command(name="platform_admin", help="Create a platform administrator user")
@username
@password
@email
@verbose
def create_platform_admin_user(username, password, email, verbose):
    app = get_app()
    with app.app_context():
        create_user_with_role(
            username,
            email,
            password,
            "platform administrator",
            PLATFORM_ADMIN_ROLE,
            verbose=verbose,
        )


@create.command(
    name="platform_viewer",
    help="Create a platform viewer user (internal, same permissions as a "
    "client viewer)",
)
@username
@password
@email
@verbose
def create_platform_viewer_user(username, password, email, verbose):
    app = get_app()
    with app.app_context():
        create_user_with_role(
            username,
            email,
            password,
            "platform viewer",
            PLATFORM_VIEWER_ROLE,
            verbose=verbose,
        )


@create.command(
    name="platform_planner",
    help="Create a platform planner user (internal, same permissions as a "
    "client planner)",
)
@username
@password
@email
@verbose
def create_platform_planner_user(username, password, email, verbose):
    app = get_app()
    with app.app_context():
        create_user_with_role(
            username,
            email,
            password,
            "platform planner",
            PLATFORM_PLANNER_ROLE,
            verbose=verbose,
        )


@users.command(
    name="unlock",
    help="Unlock a user account locked after too many failed login attempts. "
    "This is the break-glass alternative to the platform administrator "
    "unlock endpoint.",
)
@username
def unlock_user(username):
    app = get_app()
    with app.app_context():
        user = UserModel.get_one_user_by_username(username)
        if not user:
            raise ObjectDoesNotExist("User does not exist")
        user.unlock_account()
        audit(
            "account.unlocked",
            actor="cli",
            target_id=user.id,
            target=username,
            source="cli",
        )
        click.echo(f"User {username} has been unlocked")
        return True


@users.command(
    name="bi_token",
    help="[DEPRECATED] Generate a BI token for a user (valid for "
    "BI_TOKEN_DURATION_DAYS days). BI tokens are superseded by the read-only "
    "personal API keys (users api_key --read-only), which are individually "
    "revocable and get expiry warnings; this command is kept for backwards "
    "compatibility and will be removed in a future release.",
)
@username
def issue_bi_token(username):
    app = get_app()
    with app.app_context():
        user = UserModel.get_one_user_by_username(username)
        if not user:
            raise ObjectDoesNotExist("User does not exist")
        token = BIAuth.generate_token(user.id)
        app.logger.info(f"A BI token was generated for user {username} via the CLI")
        audit(
            "bitoken.issued",
            actor="cli",
            target_id=user.id,
            target=username,
            source="cli",
        )
        click.echo(token)
        return True


@users.command(
    name="api_key",
    help="Generate a personal API key for a user (valid for "
    "API_KEY_DURATION_DAYS days). Intended to be run inside the server with "
    "database access; no TOTP step-up is required because CLI access is "
    "already privileged. Generating a new key revokes the previous one. "
    "Useful for the cornflow<->airflow service account.",
)
@username
@click.option(
    "--read-only",
    is_flag=True,
    default=False,
    help="Generate a read-only key: it is refused on any request that is not "
    "a GET (useful for reporting / BI consumers).",
)
def issue_api_key(username, read_only):
    from cornflow.shared.authentication.auth import Auth

    app = get_app()
    with app.app_context():
        user = UserModel.get_one_user_by_username(username)
        if not user:
            raise ObjectDoesNotExist("User does not exist")
        scope = API_KEY_SCOPE_READ if read_only else API_KEY_SCOPE_FULL
        user.rotate_api_key(scope=scope)
        token = Auth.generate_api_key(user.id, scope=scope)
        app.logger.info(
            f"A personal API key was generated for user {username} via the "
            f"CLI (scope {scope})"
        )
        audit(
            "apikey.issued",
            actor="cli",
            target_id=user.id,
            target=username,
            source="cli",
            scope=scope,
        )
        click.echo(token)
        return True


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
