import os
import subprocess
import sys
from logging import error

import click
import cornflow
from cornflow import create_app
from cornflow.commands import (
    access_init_command,
    create_user_with_role,
    register_deployed_dags_command,
    register_dag_permissions_command,
    update_schemas_command,
)
from cornflow.shared.const import AUTH_DB, ADMIN_ROLE, SERVICE_ROLE
from cornflow_core.shared import db
from cryptography.fernet import Fernet
from flask_migrate import Migrate, upgrade


@click.command(name="init_cornflow_service", help="Initialize the service")
def init_cornflow_service():
    click.echo("Starting the service")
    os.chdir("/usr/src/app")
    ENV = os.getenv("FLASK_ENV", "development")
    os.environ["FLASK_ENV"] = ENV

    ###################################
    # Global defaults and back-compat #
    ###################################
    # Airflow global default conn
    AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD", "admin")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://webserver:8080")
    CORNFLOW_URL = os.environ.setdefault("CORNFLOW_URL", "http://cornflow:5000")
    os.environ["AIRFLOW_USER"] = AIRFLOW_USER
    os.environ["AIRFLOW_PWD"] = AIRFLOW_PWD
    os.environ["AIRFLOW_URL"] = AIRFLOW_URL
    os.environ["FLASK_APP"] = "cornflow.app"
    os.environ["SECRET_KEY"] = os.getenv("FERNET_KEY", Fernet.generate_key().decode())

    # Cornflow db defaults
    CORNFLOW_DB_HOST = os.getenv("CORNFLOW_DB_HOST", "cornflow_db")
    CORNFLOW_DB_PORT = os.getenv("CORNFLOW_DB_PORT", "5432")
    CORNFLOW_DB_USER = os.getenv("CORNFLOW_DB_USER", "cornflow")
    CORNFLOW_DB_PASSWORD = os.getenv("CORNFLOW_DB_PASSWORD", "cornflow")
    CORNFLOW_DB = os.getenv("CORNFLOW_DB", "cornflow")
    CORNFLOW_DB_CONN = os.getenv(
        "CORNFLOW_DB_CONN",
        f"postgresql://{CORNFLOW_DB_USER}:{CORNFLOW_DB_PASSWORD}@{CORNFLOW_DB_HOST}:{CORNFLOW_DB_PORT}/{CORNFLOW_DB}",
    )
    os.environ["DATABASE_URL"] = CORNFLOW_DB_CONN

    # Platform auth config and service users
    AUTH = int(os.getenv("AUTH_TYPE", AUTH_DB))
    CORNFLOW_ADMIN_USER = os.getenv("CORNFLOW_ADMIN_USER", "cornflow_admin")
    CORNFLOW_ADMIN_EMAIL = os.getenv(
        "CORNFLOW_ADMIN_EMAIL", "cornflow_admin@cornflow.com"
    )
    CORNFLOW_ADMIN_PWD = os.getenv("CORNFLOW_ADMIN_PWD", "Cornflow_admin1234")
    CORNFLOW_SERVICE_USER = os.getenv("CORNFLOW_SERVICE_USER", "service_user")
    CORNFLOW_SERVICE_EMAIL = os.getenv(
        "CORNFLOW_SERVICE_EMAIL", "service_user@cornflow.com"
    )
    CORNFLOW_SERVICE_PWD = os.getenv("CORNFLOW_SERVICE_PWD", "Service_user1234")

    # Cornflow logging and storage config
    CORNFLOW_LOGGING = os.getenv("CORNFLOW_LOGGING", "console")
    os.environ["CORNFLOW_LOGGING"] = CORNFLOW_LOGGING

    OPEN_DEPLOYMENT = os.getenv("OPEN_DEPLOYMENT", 1)
    os.environ["OPEN_DEPLOYMENT"] = str(OPEN_DEPLOYMENT)
    SIGNUP_ACTIVATED = os.getenv("SIGNUP_ACTIVATED", 1)
    os.environ["SIGNUP_ACTIVATED"] = str(SIGNUP_ACTIVATED)
    USER_ACCESS_ALL_OBJECTS = os.getenv("USER_ACCESS_ALL_OBJECTS", 0)
    os.environ["USER_ACCESS_ALL_OBJECTS"] = str(USER_ACCESS_ALL_OBJECTS)
    DEFAULT_ROLE = os.getenv("DEFAULT_ROLE", 2)
    os.environ["DEFAULT_ROLE"] = str(DEFAULT_ROLE)

    # Check LDAP parameters for active directory and show message
    if os.getenv("AUTH_TYPE") == 2:
        print(
            "WARNING: Cornflow will be deployed with LDAP Authorization. Please review your ldap auth configuration."
        )

    # check database param from docker env
    if os.getenv("DATABASE_URL") is None:
        sys.exit("FATAL: you need to provide a postgres database for Cornflow")

    # set logrotate config file
    if CORNFLOW_LOGGING == "file":
        try:
            conf = "/usr/src/app/log/*.log {\n\
            rotate 30\n \
            daily\n\
            compress\n\
            size 20M\n\
            postrotate\n\
             kill -HUP \$(cat /usr/src/app/gunicorn.pid)\n \
            endscript}"
            logrotate = subprocess.run(
                f"cat > /etc/logrotate.d/cornflow <<EOF\n {conf} \nEOF", shell=True
            )
            out_logrotate = logrotate.stdout
            print(out_logrotate)

        except error:
            print(error)

    EXTERNAL_APP = int(os.getenv("EXTERNAL_APP", 0))
    if EXTERNAL_APP == 0:
        click.echo("Starting cornflow")
        app = create_app(ENV, CORNFLOW_DB_CONN)
        with app.app_context():
            path = f"{os.path.dirname(cornflow.__file__)}/migrations"
            migrate = Migrate(app=app, db=db, directory=path)
            upgrade()
            access_init_command(0)
            if AUTH == 1 or AUTH == 0:
                create_user_with_role(
                    CORNFLOW_ADMIN_USER,
                    CORNFLOW_ADMIN_EMAIL,
                    CORNFLOW_ADMIN_PWD,
                    "admin",
                    ADMIN_ROLE,
                    verbose=1,
                )
                # create cornflow service user
                create_user_with_role(
                    CORNFLOW_SERVICE_USER,
                    CORNFLOW_SERVICE_EMAIL,
                    CORNFLOW_SERVICE_PWD,
                    "serviceuser",
                    SERVICE_ROLE,
                    verbose=1,
                )
            register_deployed_dags_command(AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PWD, 1)
            register_dag_permissions_command(OPEN_DEPLOYMENT, 1)
            update_schemas_command(AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PWD, 1)

            # execute gunicorn application
            os.system(
                "/usr/local/bin/gunicorn -c python:cornflow.gunicorn \"cornflow:create_app('$FLASK_ENV')\""
            )
    elif EXTERNAL_APP == 1:
        click.echo(
            f"Starting cornflow + {os.getenv('EXTERNAL_APP_MODULE', '../external_app')}"
        )
        os.chdir("/usr/src/external_app")

        if register_key():
            github_host = os.getenv("github_host", None)
            register_ssh_host(github_host)

            bitbucket_host = os.getenv("BITBUCKET_HOST", None)
            register_ssh_host(bitbucket_host)

        os.system("$(command -v pip) install --user -r requirements.txt")
        sys.path.append("/usr/src/external_app")
        print(f"PATH: {sys.path}")
        from importlib import import_module

        external_app = import_module(
            os.getenv("EXTERNAL_APP_MODULE", "../external_app")
        )
        app = external_app.create_app(ENV, CORNFLOW_DB_CONN)
        with app.app_context():
            path = f"{os.path.dirname(external_app.__file__)}/migrations"
            migrate = Migrate(app=app, db=db, directory=path)
            upgrade()
            access_init_command(0)
            if AUTH == 1 or AUTH == 0:
                # create cornflow admin user
                create_user_with_role(
                    CORNFLOW_ADMIN_USER,
                    CORNFLOW_ADMIN_EMAIL,
                    CORNFLOW_ADMIN_PWD,
                    "admin",
                    ADMIN_ROLE,
                    verbose=1,
                )
                # create cornflow service user
                create_user_with_role(
                    CORNFLOW_SERVICE_USER,
                    CORNFLOW_SERVICE_EMAIL,
                    CORNFLOW_SERVICE_PWD,
                    "serviceuser",
                    SERVICE_ROLE,
                    verbose=1,
                )
            register_deployed_dags_command(AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PWD, 1)
            register_dag_permissions_command(OPEN_DEPLOYMENT, 1)
            update_schemas_command(AIRFLOW_URL, AIRFLOW_USER, AIRFLOW_PWD, 1)

        os.system(
            f"/usr/local/bin/gunicorn -c python:cornflow.gunicorn "
            f"\"wsgi:create_app('$FLASK_ENV')\""
        )

    else:
        pass


def register_ssh_host(host):
    if host is not None:
        add_host = f"ssh-keyscan {host} >> /usr/src/app/.ssh/known_hosts"
        config_ssh_host = f"echo Host {host} > /usr/src/app/.ssh/config"
        config_ssh_key = 'echo "   IdentityFile /usr/src/app/.ssh/id_rsa" >> /usr/src/app/.ssh/config'
        os.system(add_host)
        os.system(config_ssh_host)
        os.system(config_ssh_key)


def register_key():
    if os.path.isfile("/usr/src/app/.ssh/id_rsa"):
        add_key = (
            "chmod 0600 /usr/src/app/.ssh/id_rsa && ssh-add /usr/src/app/.ssh/id_rsa"
        )
        os.system(add_key)
        return True
    else:
        return False
