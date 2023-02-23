import click
from cornflow.commands import access_init_command
from .utils import get_app


@click.group(name="permissions", help="Commands to manage the permissions")
def permissions():
    pass


@permissions.command(name="init", help="Initialize the permissions for the roles")
@click.option(
    "--verbose",
    "-v",
    type=bool,
    help="If the command has to be run verbose or not",
    default=0,
)
def init_permissions(verbose):
    app = get_app()
    with app.app_context():
        access_init_command(verbose=verbose)
