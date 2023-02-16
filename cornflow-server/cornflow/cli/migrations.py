import os.path
import shutil
import sys
from importlib import import_module

import click
from cornflow_core.shared import db
from flask_migrate import Migrate, migrate, upgrade
from .arguments import app_name


@click.group(name="migrations", help="Commands to manage the migrations")
def migrations():
    pass


@migrations.command(
    name="calculate", help="Calculate the migrations for an external app"
)
@app_name
@click.option(
    "--data-conn",
    "-d",
    type=str,
    help="The data connection for cornflow",
    default="postgresql://postgres:postgresadmin@localhost:5432/cornflow",
)
def calculate_migrations(app_name, data_conn):
    sys.path.append("./")

    if os.path.exists(f"./{app_name}/migrations"):
        click.echo("The migrations folder already exists")
        click.echo(f"Location: {os.path.abspath(f'./{app_name}/migrations')}")

        external_app = import_module(f"{app_name}")
        app = external_app.create_app("development", data_conn)
        with app.app_context():
            migration_client = Migrate(
                app=app, db=db, directory=f"./{app_name}/migrations"
            )
            upgrade()
            migrate()
            upgrade()

    else:
        import cornflow

        os.mkdir(f"./{app_name}/migrations")
        cornflow_migrations = os.path.dirname(cornflow.__file__) + "/migrations"
        for file in os.listdir(cornflow_migrations):
            if os.path.exists(os.path.join(f"./{app_name}/migrations", file)):
                continue
            if os.path.isfile(os.path.join(cornflow_migrations, file)):
                shutil.copy2(
                    os.path.join(cornflow_migrations, file), f"./{app_name}/migrations"
                )
            if os.path.isdir(os.path.join(cornflow_migrations, file)):
                shutil.copytree(
                    os.path.join(cornflow_migrations, file),
                    f"./{app_name}/migrations/" + file,
                )

        click.echo(f"Migrations from cornflow copied to {app_name}")
        external_app = import_module(f"{app_name}")
        app = external_app.create_app("development", data_conn)
        with app.app_context():
            migration_client = Migrate(
                app=app, db=db, directory=f"./{app_name}/migrations"
            )
            upgrade()
            migrate()
            upgrade()
