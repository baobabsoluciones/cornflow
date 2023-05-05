import os.path


import click
from cornflow.shared import db
from flask_migrate import Migrate, migrate, upgrade, init

from .utils import get_app


@click.group(name="migrations", help="Commands to manage the migrations")
def migrations():
    pass


@migrations.command(name="migrate", help="Calculate the migrations")
def migrate_migrations():
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = "./cornflow/migrations"
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        migration_client = Migrate(app=app, db=db, directory=path)
        migrate()


@migrations.command(name="upgrade", help="Apply migrations")
def upgrade_migrations():
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = "./cornflow/migrations"
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        migration_client = Migrate(app=app, db=db, directory=path)
        upgrade()


@migrations.command(
    name="init",
    help="Initialize the migrations for an external app. Creates the folder and copies the migrations from cornflow",
)
def init_migrations():
    app = get_app()
    external = int(os.getenv("EXTERNAL_APP", 0))
    if external == 0:
        path = "./cornflow/migrations"
    else:
        path = f"./{os.getenv('EXTERNAL_APP_MODULE', 'external_app')}/migrations"

    with app.app_context():
        migration_client = Migrate(app=app, db=db, directory=path)
        init()
