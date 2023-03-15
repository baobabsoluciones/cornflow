import click
from cornflow.commands import register_roles_command
from .arguments import verbose
from .utils import get_app


@click.group(name="roles", help="Commands to manage the roles")
def roles():
    pass


@roles.command(name="init", help="Initializes the roles with the default roles")
@verbose
def init(verbose):
    app = get_app()
    with app.app_context():
        register_roles_command(verbose)
