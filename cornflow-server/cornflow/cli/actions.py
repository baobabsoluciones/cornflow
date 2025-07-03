import click

from cornflow.cli.utils import get_app
from cornflow.commands import register_actions_command
from .arguments import verbose


@click.group(name="actions", help="Commands to manage the actions")
def actions():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@actions.command(name="init", help="Initialize the actions")
@verbose
def init(verbose):
    app = get_app()
    with app.app_context():
        register_actions_command(verbose)
