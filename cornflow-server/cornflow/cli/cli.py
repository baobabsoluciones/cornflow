import click
from cornflow.cli.config import config


@click.group()
def cli():
    pass


cli.add_command(config)
