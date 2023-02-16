import os

import click
from cornflow import create_app
from flask import current_app


@click.group()
def config():
    pass


@config.command(name="list", help="List the configuration variables")
def config_list():
    env = os.getenv("FLASK_ENV", "development")
    if env is None:
        click.echo("The environment variables are not set")
        return 0

    app = create_app(env)
    with app.app_context():
        for key, value in current_app.config.items():
            click.echo(f"{key} = {value}")

    return 1


@config.command(name="save", help="Save the configuration variables to a file")
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the file to save the config",
    default="./",
)
def config_save(path):
    env = os.getenv("FLASK_ENV", "development")
    if env is None:
        click.echo("The environment variables are not set")
        return 0

    app = create_app(env)
    path = f"{path}config.cfg"
    with app.app_context():
        with open(path, "w") as f:
            f.write("[configuration]\n")
            for key, value in current_app.config.items():
                f.write(f"{key} = {value}")

    return 1


@config.command(name="get", help="Get the value of a configuration variable")
@click.option("--key", "-k", type=str, help="The key of the configuration variable")
def config_get(key):
    env = os.getenv("FLASK_ENV", "development")
    if env is None:
        click.echo("The environment variables are not set")
        return 0

    app = create_app(env)
    with app.app_context():
        click.echo(f"{current_app.config.get(key, None)}")
