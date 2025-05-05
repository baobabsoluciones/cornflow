import os.path


import click
from cornflow.shared import db
from cornflow.shared.const import MIGRATIONS_DEFAULT_PATH
from flask_migrate import Migrate, migrate, upgrade, downgrade, init

from .utils import get_app


@click.group(name="migrations", help="Commands to manage the migrations")
def migrations():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@migrations.command(name="migrate", help="Calculate the migrations")
def migrate_migrations():
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = MIGRATIONS_DEFAULT_PATH
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        Migrate(app=app, db=db, directory=path)
        migrate()


@migrations.command(name="upgrade", help="Apply migrations")
@click.option(
    "-r", "--revision", type=str, help="The revision to upgrade to", default="head"
)
def upgrade_migrations(revision="head"):
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = MIGRATIONS_DEFAULT_PATH
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        Migrate(app=app, db=db, directory=path)
        upgrade(revision=revision)


@migrations.command(name="downgrade", help="Downgrade migrations")
@click.option(
    "-r", "--revision", type=str, help="The revision to downgrade to", default="-1"
)
def downgrade_migrations(revision="-1"):
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = MIGRATIONS_DEFAULT_PATH
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        Migrate(app=app, db=db, directory=path)
        downgrade(revision=revision)


@migrations.command(
    name="init",
    help="Initialize the migrations for an external app. Creates the folder and copies the migrations from cornflow",
)
def init_migrations():
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = MIGRATIONS_DEFAULT_PATH
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        Migrate(app=app, db=db, directory=path)
        init()
