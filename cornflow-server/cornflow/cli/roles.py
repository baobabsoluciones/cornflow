import os
import sys
from importlib import import_module
from .arguments import verbose
import click
from cornflow.commands import register_roles_command
from .utils import get_app


@click.group()
def roles():
    pass


@roles.command(name="init", help="Initializes the roles with the default roles")
@verbose
def init(verbose):
    app = get_app()
    with app.app_context():
        register_roles_command(verbose)
