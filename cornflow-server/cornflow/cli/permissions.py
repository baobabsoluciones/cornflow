import os

import click
from cornflow.commands import (
    access_init_command,
    register_base_permissions_command,
)
from .arguments import verbose
from .utils import get_app


@click.group(name="permissions", help="Commands to manage the permissions")
def permissions():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@permissions.command(
    name="init", help="Creates the actions, views, roles and permissions"
)
@verbose
def init_permissions(verbose):
    app = get_app()
    with app.app_context():
        access_init_command(verbose=verbose)


@permissions.command(name="base", help="Initialize the base permissions")
@verbose
def init_base(verbose):
    app = get_app()
    with app.app_context():
        external = int(os.getenv("EXTERNAL_APP", 0))
        external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
        register_base_permissions_command(verbose=verbose)
        if external != 0:
            register_base_permissions_command(
                external_app=external_app, verbose=verbose
            )
