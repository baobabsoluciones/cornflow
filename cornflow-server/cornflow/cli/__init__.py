"""
init file to have this as a module
"""

import click
from cornflow.cli.migrations import migrations
from cornflow.cli.config import config
from cornflow.cli.service import service
from cornflow.cli.permissions import permissions
from cornflow.cli.users import users


@click.group(name="cornflow", help="Commands in the cornflow cli")
def cli():
    pass


cli.add_command(config)
cli.add_command(migrations)
cli.add_command(permissions)
cli.add_command(service)
cli.add_command(users)
