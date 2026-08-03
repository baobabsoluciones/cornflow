"""
Main file with the creation of the app logic
"""

# Full imports
import os
from logging.config import dictConfig

import click

# Partial imports
from flask import Flask
from flask.cli import with_appcontext
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api
from werkzeug.exceptions import NotFound
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

# Module imports
from cornflow.commands import (
    create_service_user_command,
    create_admin_user_command,
    create_planner_user_command,
    register_roles_command,
    register_actions_command,
    register_views_command,
    register_base_permissions_command,
    access_init_command,
    register_deployed_dags_command,
    register_dag_permissions_command,
)
from cornflow.config import app_config
from cornflow.endpoints import resources, alarms_resources
from cornflow.endpoints.login import LoginEndpoint, LoginOpenAuthEndpoint
from cornflow.endpoints.refresh import LogoutEndpoint, RefreshTokenEndpoint
from cornflow.endpoints.signup import SignUpEndpoint
from cornflow.shared import db, bcrypt
from cornflow.shared.compress import init_compress
from cornflow.shared.rate_limit import limiter
from cornflow.shared.const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OID,
    CONDITIONAL_ENDPOINTS,
    SIGNUP_WITH_AUTH,
    SIGNUP_WITH_NO_AUTH,
)
from cornflow.shared.exceptions import initialize_errorhandlers, ConfigurationError
from cornflow.shared.log_config import log_config
from cornflow.shared.security import init_security_headers, resolve_cors_origins


# Minimum length in bytes of the JWT signing keys. HMAC-SHA256 requires keys
# of at least 256 bits (RFC 7518, section 3.2) and CCN-STIC-807 requires
# equivalent strength for the employed cryptography.
MINIMUM_SECRET_KEY_LENGTH = 32


def _check_secret_keys(app):
    """
    Refuses to start the application when a JWT signing key is configured
    with less than MINIMUM_SECRET_KEY_LENGTH bytes, so weak keys can not be
    used to sign session tokens.

    :param app: the Flask application being created
    """
    for key_name in ("SECRET_TOKEN_KEY", "SECRET_BI_KEY"):
        value = app.config.get(key_name)
        if value is None:
            # Token generation will fail at runtime with a clear error;
            # deployments must provide the keys through the environment
            app.logger.warning(
                f"{key_name} is not configured: authentication tokens can "
                f"not be issued until it is set"
            )
            continue
        if len(str(value).encode("utf8")) < MINIMUM_SECRET_KEY_LENGTH:
            raise ConfigurationError(
                f"{key_name} must be at least {MINIMUM_SECRET_KEY_LENGTH} "
                f"bytes long (256 bits). Generate one with: "
                f'python -c "import secrets; print(secrets.token_hex(32))"'
            )


def create_app(env_name="development", dataconn=None):
    """

    :param str env_name: 'testing' or 'development' or 'production'
    :param str dataconn: string to connect to the database
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """
    dictConfig(log_config(app_config[env_name].LOG_LEVEL))

    # Note: Explicit CSRF protection is not configured as the application uses
    # JWT for authentication via headers, mitigating standard CSRF vulnerabilities.
    app = Flask(__name__)
    app.json.sort_keys = False
    app.logger.setLevel(app_config[env_name].LOG_LEVEL)

    app.config.from_object(app_config[env_name])
    _check_secret_keys(app)
    # initialization for init_cornflow_service.py
    if dataconn is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = dataconn
    # Cross-origin access is driven by CORS_ORIGINS: "*" allows any origin
    # (development default), an explicit list restricts it and an empty value
    # (production default) is default-closed.
    CORS(app, origins=resolve_cors_origins(app.config.get("CORS_ORIGINS", "*")))
    bcrypt.init_app(app)
    db.init_app(app)
    Migrate(app=app, db=db)

    # When behind a trusted reverse proxy, honour the forwarded headers so the
    # rate limiter and the logs see the real client IP instead of the proxy's
    if int(app.config.get("RATELIMIT_TRUST_FORWARDED_FOR", 0)):
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
        )

    limiter.init_app(app)

    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        def _fk_pragma_on_connect(dbapi_con, _con_record):
            dbapi_con.execute("pragma foreign_keys=ON")

        with app.app_context():
            from sqlalchemy import event

            event.listen(db.engine, "connect", _fk_pragma_on_connect)

    api = Api(app)
    for res in resources:
        api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])
    if app.config["ALARMS_ENDPOINTS"]:
        for res in alarms_resources:
            api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])

    # The interactive API docs (Swagger UI) are registered only when enabled.
    # They are off by default in production so the deny-by-default CSP holds
    # and the OpenAPI schema is not exposed.
    if int(app.config.get("DOCS_ENABLED", 1)):
        docs = FlaskApiSpec(app)
        for res in resources:
            docs.register(target=res["resource"], endpoint=res["endpoint"])
        if app.config["ALARMS_ENDPOINTS"]:
            for res in alarms_resources:
                docs.register(target=res["resource"], endpoint=res["endpoint"])

    # Resource for the log-in
    auth_type = app.config["AUTH_TYPE"]

    if auth_type == AUTH_DB:
        signup_activated = int(app.config["SIGNUP_ACTIVATED"])
        if signup_activated in [SIGNUP_WITH_AUTH, SIGNUP_WITH_NO_AUTH]:
            api.add_resource(
                SignUpEndpoint, CONDITIONAL_ENDPOINTS["signup"], endpoint="signup"
            )
        api.add_resource(
            LoginEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login"
        )
    elif auth_type == AUTH_LDAP:
        api.add_resource(
            LoginEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login"
        )
    elif auth_type == AUTH_OID:
        api.add_resource(
            LoginOpenAuthEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login"
        )
    else:
        raise ConfigurationError(
            error="Invalid authentication type",
            log_txt="Error while configuring authentication. The authentication type is not valid.",
        )

    # Refresh-token session endpoints. Like login, they validate the token in
    # the request themselves, so they are registered outside the permission
    # system (no ViewModel / permission entries).
    api.add_resource(
        RefreshTokenEndpoint, "/token/refresh/", endpoint="token-refresh"
    )
    api.add_resource(LogoutEndpoint, "/logout/", endpoint="logout")

    initialize_errorhandlers(app)
    init_compress(app)
    init_security_headers(app)

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

    if app.config["APPLICATION_ROOT"] != "/" and app.config["EXTERNAL_APP"] == 0:
        app.wsgi_app = DispatcherMiddleware(
            NotFound(), {app.config["APPLICATION_ROOT"]: app.wsgi_app}
        )

    return app


@click.command("create_service_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def create_service_user(username, email, password, verbose):
    create_service_user_command(username, email, password, verbose)


@click.command("create_admin_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def create_admin_user(username, email, password, verbose):
    create_admin_user_command(username, email, password, verbose)


@click.command("create_base_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def create_base_user(username, email, password, verbose):
    create_planner_user_command(username, email, password, verbose)


@click.command("register_roles")
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_roles(verbose):
    register_roles_command(verbose=verbose)


@click.command("register_actions")
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_actions(verbose):
    register_actions_command(verbose)


@click.command("register_views")
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_views(verbose):
    register_views_command(verbose=verbose)


@click.command("register_base_assignations")
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_base_assignations(verbose):
    register_base_permissions_command(verbose=verbose)


@click.command("access_init")
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def access_init(verbose):
    access_init_command(verbose=verbose)


@click.command("register_deployed_dags")
@click.option("-r", "--url", type=str)
@click.option("-u", "--username", type=str)
@click.option("-p", "--password", type=str)
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_deployed_dags(url, username, password, verbose):
    register_deployed_dags_command(url, username, password, verbose)


@click.command("register_dag_permissions")
@click.option("-o", "--open_deployment", default=0, type=int)
@click.option("-v", "--verbose", is_flag=True, default=False)
@with_appcontext
def register_dag_permissions(open_deployment, verbose):
    register_dag_permissions_command(open_deployment=open_deployment, verbose=verbose)


if __name__ == "__main__":
    environment_name = os.getenv("FLASK_ENV", "development")
    flask_app = create_app(environment_name)
    flask_app.run()
