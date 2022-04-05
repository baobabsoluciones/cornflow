"""

"""
# Full imports
import click
import os

# Partial imports
from flask import Flask
from flask.cli import with_appcontext
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api

# Module imports
from .commands.access import access_init_command
from .commands.actions import register_actions_command
from .commands.dag import register_deployed_dags_command
from .commands.permissions import (
    register_base_permissions_command,
    register_dag_permissions_command,
)
from .commands.roles import register_roles_command
from .commands.users import (
    create_admin_user_command,
    create_planner_user_command,
    create_service_user_command,
)
from .commands.views import register_views_command
from .config import app_config
from .endpoints import resources
from .endpoints.login import LoginEndpoint, LoginOpenAuthEndpoint
from .shared.compress import init_compress
from cornflow_backend.exceptions import initialize_errorhandlers

# from .shared.exceptions import initialize_errorhandlers
from .shared.utils import db, bcrypt
from .shared.const import AUTH_DB, AUTH_LDAP, AUTH_OID


def create_app(env_name="development", dataconn=None):
    """

    :param str env_name: 'testing' or 'development' or 'production'
    :param str dataconn: string to connect to the database
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """

    app = Flask(__name__)
    app.config.from_object(app_config[env_name])
    # initialization for init_cornflow_service.py
    if dataconn is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = dataconn
    CORS(app)
    bcrypt.init_app(app)
    db.init_app(app)
    migrate = Migrate(app=app, db=db)

    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute("pragma foreign_keys=ON")

        with app.app_context():
            from sqlalchemy import event

            event.listen(db.engine, "connect", _fk_pragma_on_connect)

    api = Api(app)
    for res in resources:
        api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])

    docs = FlaskApiSpec(app)
    for res in resources:
        docs.register(target=res["resource"], endpoint=res["endpoint"])

    # Resource for the log-in
    AUTH_TYPE = app.config["AUTH_TYPE"]

    if AUTH_TYPE == AUTH_DB or AUTH_TYPE == AUTH_LDAP:
        api.add_resource(LoginEndpoint, "/login/", endpoint="login")
    elif AUTH_TYPE == AUTH_OID:
        api.add_resource(LoginOpenAuthEndpoint, "/login/", endpoint="login")

    initialize_errorhandlers(app)
    init_compress(app)

    app.cli.add_command(create_service_user)
    app.cli.add_command(create_admin_user)
    app.cli.add_command(register_roles)
    app.cli.add_command(create_base_user)
    app.cli.add_command(register_actions)
    app.cli.add_command(register_views)
    app.cli.add_command(register_base_assignations)
    app.cli.add_command(access_init)
    app.cli.add_command(register_deployed_dags)
    app.cli.add_command(register_dag_permissions)

    return app


@click.command("create_service_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", default=0)
@with_appcontext
def create_service_user(username, email, password, verbose):
    create_service_user_command(username, email, password, verbose)


@click.command("create_admin_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def create_admin_user(username, email, password, verbose):
    create_admin_user_command(username, email, password, verbose)


@click.command("create_base_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def create_base_user(username, email, password, verbose):
    create_planner_user_command(username, email, password, verbose)


@click.command("register_roles")
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_roles(verbose):
    register_roles_command(verbose)


@click.command("register_actions")
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_actions(verbose):
    register_actions_command(verbose)


@click.command("register_views")
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_views(verbose):
    register_views_command(verbose)


@click.command("register_base_assignations")
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_base_assignations(verbose):
    register_base_permissions_command(verbose)


@click.command("access_init")
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def access_init(verbose):
    access_init_command(verbose)


@click.command("register_deployed_dags")
@click.option("-r", "--url", type=str)
@click.option("-u", "--username", type=str)
@click.option("-p", "--password", type=str)
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_deployed_dags(url, username, password, verbose):
    register_deployed_dags_command(url, username, password, verbose)


@click.command("register_dag_permissions")
@click.option("-o", "--open_deployment", default=0, type=int)
@click.option("-v", "--verbose", type=int, default=0)
@with_appcontext
def register_dag_permissions(open_deployment, verbose):
    register_dag_permissions_command(open_deployment=open_deployment, verbose=verbose)


if __name__ == "__main__":
    environment_name = os.getenv("FLASK_ENV", "development")
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()
