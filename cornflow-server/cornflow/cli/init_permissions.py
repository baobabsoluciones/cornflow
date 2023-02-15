import os.path
import sys
from importlib import import_module

import click
from cornflow_core.shared import db
from flask_migrate import Migrate, upgrade


@click.command(name="init_permissions", help="Initialize the permissions for the roles")
@click.option(
    "--app-name",
    "-a",
    type=str,
    help="The name of the external app",
    default="external_app",
)
@click.option(
    "--data-conn",
    "-d",
    type=str,
    help="The data connection for cornflow",
    default="postgresql://postgres:postgresadmin@localhost:5432/cornflow",
)
@click.option(
    "--verbose",
    "-v",
    type=bool,
    help="If the command has to be run verbose or not",
    default=0,
)
def init_permissions(app_name, data_conn, verbose):
    sys.path.append("./")
    from cornflow.commands import access_init_command

    external_app = import_module(f"{app_name}")
    app = external_app.create_app(environment="development", dataconn=data_conn)
    with app.app_context():
        path = f"{os.path.dirname(external_app.__file__)}/migrations"
        migrate = Migrate(app=app, db=db, directory=path)
        upgrade()
        access_init_command(external_app=external_app, verbose=verbose)
