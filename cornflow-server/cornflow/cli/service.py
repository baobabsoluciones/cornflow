import os
import subprocess
import sys
import time
from logging import error


import click
from .utils import get_db_conn
import cornflow
from cornflow.app import create_app
from cornflow.commands import (
    access_init_command,
    create_user_with_role,
    register_deployed_dags_command,
    register_dag_permissions_command,
    update_schemas_command,
    update_dag_registry_command,
)
from cornflow.shared.const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OID,
    ADMIN_ROLE,
    SERVICE_ROLE,
    PLANNER_ROLE,
)
from cornflow.shared import db
from cryptography.fernet import Fernet
from flask_migrate import Migrate, upgrade

MAIN_WD = "/usr/src/app"


@click.group(name="service", help="Commands to run the cornflow service")
def service():
    """
    This method is empty but it serves as the building block
    for the rest of the commands
    """
    pass


@service.command(name="init", help="Initialize the service")
def init_cornflow_service():
    click.echo("Starting the service")
    os.chdir(MAIN_WD)

    config = _setup_environment_variables()
    _configure_logging(config["cornflow_logging"])

    external_application = config["external_application"]
    environment = config["environment"]
    cornflow_db_conn = config["cornflow_db_conn"]
    external_app_module = config["external_app_module"]

    app = None  # Initialize app to None

    if external_application == 0:
        click.echo("Initializing standard Cornflow application")
        app = create_app(environment, cornflow_db_conn)
        with app.app_context():
            _initialize_database(app)
            _create_initial_users(
                config["auth"],
                config["cornflow_admin_user"],
                config["cornflow_admin_email"],
                config["cornflow_admin_pwd"],
                config["cornflow_service_user"],
                config["cornflow_service_email"],
                config["cornflow_service_pwd"],
            )
            _sync_with_airflow(
                config["airflow_url"],
                config["airflow_user"],
                config["airflow_pwd"],
                config["open_deployment"],
                external_app=False,
            )
        _start_application(external_application, environment)

    elif external_application == 1:
        click.echo(f"Initializing Cornflow with external app: {external_app_module}")
        if not external_app_module:
            sys.exit("FATAL: EXTERNAL_APP is 1 but EXTERNAL_APP_MODULE is not set.")

        _setup_external_app()
        from importlib import import_module

        external_app_lib = import_module(external_app_module)
        app = external_app_lib.create_wsgi_app(environment, cornflow_db_conn)

        with app.app_context():
            _initialize_database(app, external_app_module)
            _create_initial_users(
                config["auth"],
                config["cornflow_admin_user"],
                config["cornflow_admin_email"],
                config["cornflow_admin_pwd"],
                config["cornflow_service_user"],
                config["cornflow_service_email"],
                config["cornflow_service_pwd"],
            )
            _sync_with_airflow(
                config["airflow_url"],
                config["airflow_user"],
                config["airflow_pwd"],
                config["open_deployment"],
                external_app=True,
            )
        _start_application(external_application, environment, external_app_module)

    else:
        # This case should ideally be caught earlier or handled differently
        sys.exit(f"FATAL: Invalid EXTERNAL_APP value: {external_application}")


def _setup_environment_variables():
    """Reads environment variables, sets defaults, and returns config values."""
    environment = os.getenv("FLASK_ENV", "development")
    os.environ["FLASK_ENV"] = environment

    # Airflow details
    airflow_user = os.getenv("AIRFLOW_USER", "admin")
    airflow_pwd = os.getenv("AIRFLOW_PWD", "admin")
    airflow_url = os.getenv("AIRFLOW_URL", "http://webserver:8080")
    os.environ["AIRFLOW_USER"] = airflow_user
    os.environ["AIRFLOW_PWD"] = airflow_pwd
    os.environ["AIRFLOW_URL"] = airflow_url

    # Cornflow app config
    os.environ.setdefault("cornflow_url", "http://cornflow:5000")
    os.environ["FLASK_APP"] = "cornflow.app"
    os.environ["SECRET_KEY"] = os.getenv("FERNET_KEY", Fernet.generate_key().decode())

    # Cornflow db defaults
    os.environ["DEFAULT_POSTGRES"] = "1"
    cornflow_db_conn = get_db_conn()
    os.environ["DATABASE_URL"] = cornflow_db_conn

    # Platform auth config and service users
    auth = int(os.getenv("AUTH_TYPE", AUTH_DB))
    cornflow_admin_user = os.getenv("CORNFLOW_ADMIN_USER", "cornflow_admin")
    cornflow_admin_email = os.getenv(
        "CORNFLOW_ADMIN_EMAIL", "cornflow_admin@cornflow.com"
    )
    cornflow_admin_pwd = os.getenv("CORNFLOW_ADMIN_PWD", "Cornflow_admin1234")
    cornflow_service_user = os.getenv("CORNFLOW_SERVICE_USER", "service_user")
    cornflow_service_email = os.getenv(
        "CORNFLOW_SERVICE_EMAIL", "service_user@cornflow.com"
    )
    cornflow_service_pwd = os.getenv("CORNFLOW_SERVICE_PWD", "Service_user1234")

    # Cornflow logging and deployment config
    cornflow_logging = os.getenv("CORNFLOW_LOGGING", "console")
    os.environ["CORNFLOW_LOGGING"] = cornflow_logging
    open_deployment = os.getenv("OPEN_DEPLOYMENT", 1)
    os.environ["OPEN_DEPLOYMENT"] = str(open_deployment)
    signup_activated = os.getenv("SIGNUP_ACTIVATED", 1)
    os.environ["SIGNUP_ACTIVATED"] = str(signup_activated)
    user_access_all_objects = os.getenv("USER_ACCESS_ALL_OBJECTS", 0)
    os.environ["USER_ACCESS_ALL_OBJECTS"] = str(user_access_all_objects)
    default_role = int(os.getenv("DEFAULT_ROLE", PLANNER_ROLE))
    os.environ["DEFAULT_ROLE"] = str(default_role)

    # Check LDAP parameters for active directory and show message
    if auth == AUTH_LDAP:
        click.echo(
            "WARNING: Cornflow will be deployed with LDAP Authorization. "
            "Please review your ldap auth configuration."
        )

    # check database param from docker env
    if cornflow_db_conn is None:
        sys.exit("FATAL: you need to provide a postgres database for Cornflow")

    external_application = int(os.getenv("EXTERNAL_APP", 0))
    external_app_module = os.getenv("EXTERNAL_APP_MODULE")

    return {
        "environment": environment,
        "auth": auth,
        "airflow_user": airflow_user,
        "airflow_pwd": airflow_pwd,
        "airflow_url": airflow_url,
        "cornflow_db_conn": cornflow_db_conn,
        "cornflow_admin_user": cornflow_admin_user,
        "cornflow_admin_email": cornflow_admin_email,
        "cornflow_admin_pwd": cornflow_admin_pwd,
        "cornflow_service_user": cornflow_service_user,
        "cornflow_service_email": cornflow_service_email,
        "cornflow_service_pwd": cornflow_service_pwd,
        "cornflow_logging": cornflow_logging,
        "open_deployment": open_deployment,
        "external_application": external_application,
        "external_app_module": external_app_module,
    }


def _configure_logging(cornflow_logging):
    """Configures log rotation if logging to file."""
    if cornflow_logging == "file":
        try:
            conf = f"""/usr/src/app/log/*.log {{
            rotate 30
            daily
            compress
            size 20M
            postrotate
             kill -HUP $(cat {MAIN_WD}/gunicorn.pid)
            endscript}}"""
            logrotate = subprocess.run(
                f"cat > /etc/logrotate.d/cornflow <<EOF\n {conf} \nEOF",
                shell=True,
                capture_output=True,
                text=True,
            )
            if logrotate.returncode != 0:
                error(f"Error configuring logrotate: {logrotate.stderr}")
            else:
                print(logrotate.stdout)
        except Exception as e:
            error(f"Exception during logrotate configuration: {e}")


def _initialize_database(app, external_app_module=None):
    """Initializes the database and runs migrations."""
    with app.app_context():
        if external_app_module:
            from importlib import import_module

            external_app_lib = import_module(external_app_module)
            migrations_path = f"{os.path.dirname(external_app_lib.__file__)}/migrations"
        else:
            migrations_path = f"{os.path.dirname(cornflow.__file__)}/migrations"

        Migrate(app=app, db=db, directory=migrations_path)
        upgrade()
        access_init_command(verbose=False)


def _create_initial_users(
    auth,
    admin_user,
    admin_email,
    admin_pwd,
    service_user,
    service_email,
    service_pwd,
):
    """Creates the initial admin and service users if using DB or OID auth."""
    if auth == AUTH_DB or auth == AUTH_OID:
        # create cornflow admin user
        create_user_with_role(
            admin_user,
            admin_email,
            admin_pwd,
            "admin",
            ADMIN_ROLE,
            verbose=True,
        )
        # create cornflow service user
        create_user_with_role(
            service_user,
            service_email,
            service_pwd,
            "serviceuser",
            SERVICE_ROLE,
            verbose=True,
        )


def _sync_with_airflow(
    airflow_url, airflow_user, airflow_pwd, open_deployment, external_app=False
):
    """Syncs DAGs, permissions, and schemas with Airflow."""
    register_deployed_dags_command(airflow_url, airflow_user, airflow_pwd, verbose=True)
    register_dag_permissions_command(open_deployment, verbose=True)
    update_schemas_command(airflow_url, airflow_user, airflow_pwd, verbose=True)
    if external_app:
        update_dag_registry_command(
            airflow_url, airflow_user, airflow_pwd, verbose=True
        )


def _setup_external_app():
    """Performs setup steps specific to external applications."""
    os.chdir(MAIN_WD)
    if _register_key():
        prefix = "CUSTOM_SSH_"
        env_variables = {
            key: value for key, value in os.environ.items() if key.startswith(prefix)
        }
        for _, value in env_variables.items():
            _register_ssh_host(value)

    # Install requirements for the external app
    pip_install_cmd = "$(command -v pip) install --user -r requirements.txt"
    click.echo(f"Running: {pip_install_cmd}")
    result = subprocess.run(pip_install_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"Error installing requirements: {result.stderr}")
    else:
        print(result.stdout)
    time.sleep(5)  # Consider if this sleep is truly necessary
    sys.path.append(MAIN_WD)


def _start_application(external_application, environment, external_app_module=None):
    """Starts the Gunicorn server."""
    if external_application == 0:
        os.environ["GUNICORN_WORKING_DIR"] = MAIN_WD
        gunicorn_cmd = (
            "/usr/local/bin/gunicorn -c python:cornflow.gunicorn "
            f"\"cornflow.app:create_app('{environment}')\""
        )
    elif external_application == 1:
        os.environ["GUNICORN_WORKING_DIR"] = MAIN_WD
        if not external_app_module:
            raise ValueError(
                "EXTERNAL_APP_MODULE must be set for external applications"
            )
        gunicorn_cmd = (
            "/usr/local/bin/gunicorn -c python:cornflow.gunicorn "
            f"\"{external_app_module}:create_wsgi_app('{environment}')\""
        )
    else:
        raise ValueError(f"Invalid EXTERNAL_APP value: {external_application}")

    click.echo(f"Starting application with Gunicorn: {gunicorn_cmd}")
    os.system(gunicorn_cmd)


def _register_ssh_host(host):
    if host is not None:
        add_host = f"ssh-keyscan {host} >> {MAIN_WD}/.ssh/known_hosts"
        config_ssh_host = f"echo Host {host} >> {MAIN_WD}/.ssh/config"
        config_ssh_key = (
            'echo "   IdentityFile {MAIN_WD}/.ssh/id_rsa" >> {MAIN_WD}/.ssh/config'
        )
        os.system(add_host)
        os.system(config_ssh_host)
        os.system(config_ssh_key)


def _register_key():
    if os.path.isfile(f"{MAIN_WD}/.ssh/id_rsa"):
        add_key = f"chmod 0600 {MAIN_WD}/.ssh/id_rsa && ssh-add {MAIN_WD}/.ssh/id_rsa"
        os.system(add_key)
        return True
    else:
        return False
