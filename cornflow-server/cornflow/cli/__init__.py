"""
init file to have this as a module
"""

import click

from cornflow.cli.actions import actions
from cornflow.cli.config import config
from cornflow.cli.migrations import migrations
from cornflow.cli.permissions import permissions
from cornflow.cli.roles import roles
from cornflow.cli.schemas import schemas
from cornflow.cli.service import service
from cornflow.cli.users import users
from cornflow.cli.views import views


@click.group(name="cornflow", help="Commands in the cornflow cli")
def cli():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


cli.add_command(actions)
cli.add_command(config)
cli.add_command(migrations)
cli.add_command(permissions)
cli.add_command(roles)
cli.add_command(schemas)
cli.add_command(service)
cli.add_command(users)
cli.add_command(views)
