"""
Main file with the creation of the app logic
"""

# Full imports
import os
from logging.config import dictConfig

import click

# Partial imports
from flask import Flask, Blueprint
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
    LEGACY_ENDPOINT_SUFFIX,
    SIGNUP_PLATFORM_ADMIN_ONLY,
    SIGNUP_WITH_AUTH,
    SIGNUP_WITH_NO_AUTH,
)
from cornflow.shared.exceptions import initialize_errorhandlers, ConfigurationError
from cornflow.shared.log_config import log_config
from cornflow.shared.plugins import load_plugins
from cornflow.shared.security import init_security_headers, resolve_cors_origins
from cornflow.shared.security_levels import (
    CONFIG_KEY_ADJUSTED,
    CONFIG_KEY_CHANGED,
    CONFIG_KEY_ERRORS,
    CONFIG_KEY_LEVEL,
    CONFIG_KEY_LEVEL_ERROR,
    DEFAULT_SECURITY_LEVEL,
)
from cornflow.shared.secret_keys import (
    CONFIG_KEY_SECRET_KEY_SOURCE,
    CONFIG_KEY_SECRET_KEYS_DIFFER,
    KEY_SOURCE_CONFIG,
    MINIMUM_SECRET_KEY_LENGTH,  # noqa: F401 (imported by the tests from here)
    check_secret_keys,
)


# Settings that only work with the MFA endpoints enabled
MFA_DEPENDENT_SETTINGS = ("MFA_REQUIRED", "API_KEY_STEPUP_TOTP", "PLATFORM_ROLE_STEPUP_TOTP")


def _check_security_level(app):
    """
    Refuses to start with an invalid CORNFLOW_SECURITY_LEVEL. config.py
    records the error instead of raising, so the import never fails.
    """
    message = app.config.get(CONFIG_KEY_LEVEL_ERROR)
    if message:
        raise ConfigurationError(error=message, log_txt=message)


def _check_disabling_zeros(app):
    """
    Refuses to start when a security setting is set to a value <= 0 that turns
    a control off and the security level does not allow it (LOGIN_MAX_ATTEMPTS
    at levels 2 and 3, BI_TOKEN_DURATION_DAYS at level 3).
    """
    errors = tuple(app.config.get(CONFIG_KEY_ERRORS) or ())
    if errors:
        message = "; ".join(errors)
        raise ConfigurationError(error=message, log_txt=message)


def _check_mfa_coherence(app):
    """
    Refuses to start when a setting that needs the MFA endpoints is on while
    MFA_ENABLED is off. MFA_ENABLED is never forced to 1.
    """
    mfa_enabled = int(app.config.get("MFA_ENABLED", 0))
    if mfa_enabled == 1:
        return
    enabled = [
        name for name in MFA_DEPENDENT_SETTINGS if int(app.config.get(name, 0)) == 1
    ]
    if not enabled:
        return
    names = ", ".join(enabled)
    assignments = ", ".join(f"{name}=1" for name in enabled)
    verb = "needs" if len(enabled) == 1 else "need"
    message = (
        f"{assignments} {verb} MFA_ENABLED=1, but MFA_ENABLED is {mfa_enabled}: "
        f"set MFA_ENABLED=1, or set {names} to 0"
    )
    raise ConfigurationError(error=message, log_txt=message)


def _log_security_level(app):
    """
    Logs the effective security level, the variables that change a level
    default (INFO) and the ones clamped to a limit or not parseable (WARNING).
    Key values are never logged: the sensitive settings hide their value.
    """
    level = app.config.get(CONFIG_KEY_LEVEL)
    app.logger.info(f"Security level: {level}")
    for change in app.config.get(CONFIG_KEY_CHANGED) or ():
        app.logger.info(
            f"Security level {level}, changed setting: {change.as_log_text()}"
        )
    for adjustment in app.config.get(CONFIG_KEY_ADJUSTED) or ():
        app.logger.warning(
            f"Security level {level}, adjusted setting: {adjustment.as_log_text()}"
        )


def _run_startup_checks(app):
    """
    Startup checks of the security configuration, in this order: security
    level, disabling zeros the level does not allow, secret keys, MFA_ENABLED
    coherence, security level log and session windows. The checks raise
    ConfigurationError when cornflow must not start; the last two only log.
    """
    _check_security_level(app)
    _check_disabling_zeros(app)
    _check_secret_keys(app)
    _check_mfa_coherence(app)
    _log_security_level(app)
    _check_session_windows(app)


def _check_secret_keys(app):
    """
    Step 3 of the startup checks: the effective secret key (FERNET_KEY, else
    SECRET_KEY, else random at level 1) and SECRET_BI_KEY, per security level.
    Logs the warnings and raises ConfigurationError with every error joined
    with "; ". Key values are never logged.
    """
    warnings, errors = check_secret_keys(
        level=app.config.get(CONFIG_KEY_LEVEL, DEFAULT_SECURITY_LEVEL),
        token_key=app.config.get("SECRET_TOKEN_KEY"),
        source=app.config.get(CONFIG_KEY_SECRET_KEY_SOURCE, KEY_SOURCE_CONFIG),
        keys_differ=bool(app.config.get(CONFIG_KEY_SECRET_KEYS_DIFFER, False)),
        bi_key=app.config.get("SECRET_BI_KEY"),
        mfa_enabled=int(app.config.get("MFA_ENABLED", 0)) == 1,
    )
    for message in warnings:
        app.logger.warning(message)
    if errors:
        message = "; ".join(errors)
        raise ConfigurationError(error=message, log_txt=message)


def _check_session_windows(app):
    """
    Warns when the session windows are configured in a way that would log out
    users who are actively working.

    Activity is only recorded when the client exchanges the refresh token, and
    a client only does that once its access token has expired. So an
    inactivity window that is not longer than the access-token lifetime closes
    the session of an active user: by the time the client refreshes, the
    window has already elapsed. The same applies to an absolute cap shorter
    than the inactivity window, which would make the window unreachable.

    These are misconfigurations rather than security weaknesses (they are
    stricter, not laxer), so they are reported and not clamped.

    :param app: the Flask application being created
    """
    if int(app.config.get("REFRESH_TOKEN_ENABLED", 1)) != 1:
        return
    access = int(app.config.get("ACCESS_TOKEN_DURATION_MINUTES", 15))
    inactivity = int(app.config.get("REFRESH_TOKEN_INACTIVITY_MINUTES", 30))
    absolute_minutes = int(app.config.get("REFRESH_TOKEN_ABSOLUTE_HOURS", 12)) * 60
    if inactivity <= access:
        app.logger.warning(
            f"REFRESH_TOKEN_INACTIVITY_MINUTES ({inactivity}) is not greater "
            f"than ACCESS_TOKEN_DURATION_MINUTES ({access}): users who are "
            f"actively working will be logged out, because a client only "
            f"refreshes its session once the access token has expired. Set "
            f"the inactivity window above the access-token lifetime "
            f"(defaults: 15 and 30)."
        )
    if absolute_minutes <= inactivity:
        app.logger.warning(
            f"REFRESH_TOKEN_ABSOLUTE_HOURS ({absolute_minutes // 60}h) is not "
            f"longer than REFRESH_TOKEN_INACTIVITY_MINUTES ({inactivity} min): "
            f"every session will end at the absolute cap and the inactivity "
            f"window will never apply."
        )


def _check_rate_limit_storage(app):
    """
    Warns at startup when the rate limiter keeps its counters in memory.
    The in-memory storage is per process: behind gunicorn every worker counts
    on its own, so a client is only throttled after the configured limit
    times the number of workers, and the remaining-requests header jumps up
    and down depending on the worker that answers. Production deployments
    must point RATELIMIT_STORAGE_URI to a shared storage (e.g. redis://).

    :param app: the Flask application being created
    """
    if not int(app.config.get("RATELIMIT_ENABLED", 0)):
        return
    storage = str(app.config.get("RATELIMIT_STORAGE_URI") or "memory://")
    if storage.startswith("memory://"):
        app.logger.warning(
            "RATELIMIT_STORAGE_URI is memory://: the rate-limit counters are "
            "kept per process, so with several gunicorn workers each one "
            "counts on its own and the effective limit is the configured one "
            "times the number of workers. Set RATELIMIT_STORAGE_URI to a "
            "shared storage (e.g. redis://<host>:6379/0) in production."
        )


def _register_legacy_routes(app, resources, alarms_resources, auth_type):
    """
    Registers the unprefixed routes (e.g. ``/login/``) kept for backwards
    compatibility. The canonical routes live under ``/cornflow/``.

    Every alias is named ``<endpoint>`` + ``LEGACY_ENDPOINT_SUFFIX``. To remove
    the unprefixed routes, delete this function and its call in ``create_app``.
    """
    suffix = LEGACY_ENDPOINT_SUFFIX
    api_legacy = Api(app)
    for res in resources:
        api_legacy.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"] + suffix)
    if app.config["ALARMS_ENDPOINTS"]:
        for res in alarms_resources:
            api_legacy.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"] + suffix)
    if auth_type == AUTH_DB:
        signup_activated = int(app.config["SIGNUP_ACTIVATED"])
        if signup_activated in [
            SIGNUP_WITH_AUTH,
            SIGNUP_WITH_NO_AUTH,
            SIGNUP_PLATFORM_ADMIN_ONLY,
        ]:
            api_legacy.add_resource(SignUpEndpoint, CONDITIONAL_ENDPOINTS["signup"], endpoint="signup" + suffix)
        api_legacy.add_resource(LoginEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login" + suffix)
    elif auth_type == AUTH_LDAP:
        api_legacy.add_resource(LoginEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login" + suffix)
    elif auth_type == AUTH_OID:
        api_legacy.add_resource(LoginOpenAuthEndpoint, CONDITIONAL_ENDPOINTS["login"], endpoint="login" + suffix)
    api_legacy.add_resource(RefreshTokenEndpoint, "/token/refresh/", endpoint="token-refresh" + suffix)
    api_legacy.add_resource(LogoutEndpoint, "/logout/", endpoint="logout" + suffix)


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
    _run_startup_checks(app)
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
    _check_rate_limit_storage(app)

    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        def _fk_pragma_on_connect(dbapi_con, _con_record):
            dbapi_con.execute("pragma foreign_keys=ON")

        with app.app_context():
            from sqlalchemy import event

            event.listen(db.engine, "connect", _fk_pragma_on_connect)

    # Rutas del Core bajo /cornflow/ via Blueprint (URLs canónicas)
    cornflow_bp = Blueprint("cornflow", __name__, url_prefix="/cornflow")
    api = Api(cornflow_bp)
    for res in resources:
        api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])
    if app.config["ALARMS_ENDPOINTS"]:
        for res in alarms_resources:
            api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])

    # Resource for the log-in
    auth_type = app.config["AUTH_TYPE"]

    if auth_type == AUTH_DB:
        signup_activated = int(app.config["SIGNUP_ACTIVATED"])
        if signup_activated in [
            SIGNUP_WITH_AUTH,
            SIGNUP_WITH_NO_AUTH,
            SIGNUP_PLATFORM_ADMIN_ONLY,
        ]:
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
    api.add_resource(RefreshTokenEndpoint, "/token/refresh/", endpoint="token-refresh")
    api.add_resource(LogoutEndpoint, "/logout/", endpoint="logout")

    app.register_blueprint(cornflow_bp)

    _register_legacy_routes(app, resources, alarms_resources, auth_type)

    # The interactive API docs (Swagger UI) are registered only when enabled.
    # They are off by default in production so the deny-by-default CSP holds
    # and the OpenAPI schema is not exposed. Only the Blueprint routes are
    # documented; the legacy aliases are not duplicated in the schema.
    if int(app.config.get("DOCS_ENABLED", 1)):
        docs = FlaskApiSpec(app)
        for res in resources:
            docs.register(target=res["resource"], endpoint=res["endpoint"], blueprint="cornflow")
        if app.config["ALARMS_ENDPOINTS"]:
            for res in alarms_resources:
                docs.register(target=res["resource"], endpoint=res["endpoint"], blueprint="cornflow")

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

    if int(app.config["EXTERNAL_APP"]) == 1:
        # Legacy mode: DispatcherMiddleware mounts cornflow under APPLICATION_ROOT.
        # The external app is responsible for combining both apps via wsgi.py.
        if app.config["APPLICATION_ROOT"] != "/":
            app.wsgi_app = DispatcherMiddleware(
                NotFound(), {app.config["APPLICATION_ROOT"]: app.wsgi_app}
            )
    else:
        # Plugin mode: autodiscover and mount plugins registered under cornflow.plugins.
        load_plugins(app)

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
