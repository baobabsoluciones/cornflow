import os

import click
from cornflow.commands import register_views_command
from .arguments import verbose
from .utils import get_app


@click.group(name="views", help="Commands to manage the views")
def views():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@views.command(name="init", help="Initialize the views")
@verbose
def init(verbose):
    app = get_app()
    with app.app_context():
        external = int(os.getenv("EXTERNAL_APP", 0))
        external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
        register_views_command(verbose=verbose)
        if external != 0:
            register_views_command(external_app=external_app, verbose=verbose)
