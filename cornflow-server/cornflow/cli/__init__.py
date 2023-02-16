"""
init file to have this as a module
"""

import click
from cornflow.cli.calculate_migrations import calculate_migrations
from cornflow.cli.config import config
from cornflow.cli.init_cornflow_service import init_cornflow_service
from cornflow.cli.init_permissions import init_permissions


@click.group(name="cornflow", help="Commands in the cornflow cli")
def cli():
    pass


cli.add_command(config)
cli.add_command(calculate_migrations)
cli.add_command(init_permissions)
cli.add_command(init_cornflow_service)
