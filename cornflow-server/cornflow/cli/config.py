import os

import click
from cornflow import create_app
from flask import current_app


@click.command(name="config_list", help="List the configuration variables")
def config_list():
    env = os.getenv("FLASK_ENV", None)
    if env is None:
        click.echo("The environment variables are not set")
        return 0

    app = create_app(env)
    with app.app_context():
        for key, value in current_app.config.items():
            click.echo(f"{key} = {value}")

    return 1
