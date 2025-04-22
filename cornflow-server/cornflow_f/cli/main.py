"""
Main CLI module that registers all command groups
"""

import click
from cornflow_f.cli.users import users
from cornflow_f.cli.roles import roles
from cornflow_f.cli.assignments import assignments
from cornflow_f.cli.permissions import permissions


@click.group()
def cli():
    """
    Cornflow CLI for managing users, roles, and permissions
    """
    pass


# Register all command groups
cli.add_command(users)
cli.add_command(roles)
cli.add_command(assignments)
cli.add_command(permissions)


if __name__ == "__main__":
    cli()
