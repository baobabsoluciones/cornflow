import click

from cornflow.cli.utils import get_app
from flask import current_app
from .arguments import path


@click.group(name="config", help="Commands to manage the configuration variables")
def config():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@config.command(name="list", help="List the configuration variables")
def config_list():
    app = get_app()
    with app.app_context():
        for key, value in current_app.config.items():
            click.echo(f"{key} = {value}")

    return 1


@config.command(name="save", help="Save the configuration variables to a file")
@path
def config_save(path):
    app = get_app()
    path = f"{path}config.cfg"
    with app.app_context():
        with open(path, "w") as f:
            f.write("[configuration]\n\n")
            for key, value in current_app.config.items():
                f.write(f"{key} = {value}\n")

    return 1


@config.command(name="get", help="Get the value of a configuration variable")
@click.option("--key", "-k", type=str, help="The key of the configuration variable")
def config_get(key):
    app = get_app()
    with app.app_context():
        click.echo(f"{current_app.config.get(key, None)}")
