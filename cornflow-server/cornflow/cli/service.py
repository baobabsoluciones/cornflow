import os
import subprocess
import sys
import time
from logging import error


import click
import cornflow
from cornflow.app import create_app
from cornflow.commands import (
    access_init_command,
    create_user_with_role,
    register_deployed_dags_command,
    register_dag_permissions_command,
    update_schemas_command,
)
from cornflow.shared.const import AUTH_DB, ADMIN_ROLE, SERVICE_ROLE
from cornflow.shared import db
from cryptography.fernet import Fernet
from flask_migrate import Migrate, upgrade


@click.group(name="service", help="Commands to run the cornflow service")
def service():
    pass


@service.command(name="init", help="Initialize the service")
def init_cornflow_service():
    click.echo("Starting the service")
    os.chdir("/usr/src/app")
    environment = os.getenv("FLASK_ENV", "development")
    os.environ["FLASK_ENV"] = environment

    ###################################
    # Global defaults and back-compat #
    ###################################
    # Airflow global default conn
    airflow_user = os.getenv("AIRFLOW_USER", "admin")
    airflow_pwd = os.getenv("AIRFLOW_PWD", "admin")
    airflow_url = os.getenv("AIRFLOW_URL", "http://webserver:8080")
    cornflow_url = os.environ.setdefault("cornflow_url", "http://cornflow:5000")
    os.environ["AIRFLOW_USER"] = airflow_user
    os.environ["AIRFLOW_PWD"] = airflow_pwd
    os.environ["AIRFLOW_URL"] = airflow_url
    os.environ["FLASK_APP"] = "cornflow.app"
    os.environ["SECRET_KEY"] = os.getenv("FERNET_KEY", Fernet.generate_key().decode())

    # Cornflow db defaults
    cornflow_db_host = os.getenv("CORNFLOW_DB_HOST", "cornflow_db")
    cornflow_db_port = os.getenv("CORNFLOW_DB_PORT", "5432")
    cornflow_db_user = os.getenv("CORNFLOW_DB_USER", "cornflow")
    cornflow_db_password = os.getenv("CORNFLOW_DB_PASSWORD", "cornflow")
    cornflow_db = os.getenv("CORNFLOW_DB", "cornflow")
    cornflow_db_conn = os.getenv(
        "cornflow_db_conn",
        f"postgresql://{cornflow_db_user}:{cornflow_db_password}@{cornflow_db_host}:{cornflow_db_port}/{cornflow_db}",
    )
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

    # Cornflow logging and storage config
    cornflow_logging = os.getenv("CORNFLOW_LOGGING", "console")
    os.environ["CORNFLOW_LOGGING"] = cornflow_logging

    open_deployment = os.getenv("OPEN_DEPLOYMENT", 1)
    os.environ["OPEN_DEPLOYMENT"] = str(open_deployment)
    signup_activated = os.getenv("SIGNUP_ACTIVATED", 1)
    os.environ["SIGNUP_ACTIVATED"] = str(signup_activated)
    user_access_all_objects = os.getenv("USER_ACCESS_ALL_OBJECTS", 0)
    os.environ["USER_ACCESS_ALL_OBJECTS"] = str(user_access_all_objects)
    default_role = os.getenv("DEFAULT_ROLE", 2)
    os.environ["DEFAULT_ROLE"] = str(default_role)

    # Check LDAP parameters for active directory and show message
    if os.getenv("AUTH_TYPE") == 2:
        print(
            "WARNING: Cornflow will be deployed with LDAP Authorization. Please review your ldap auth configuration."
        )

    # check database param from docker env
    if os.getenv("DATABASE_URL") is None:
        sys.exit("FATAL: you need to provide a postgres database for Cornflow")

    # set logrotate config file
    if cornflow_logging == "file":
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

    external_application = int(os.getenv("EXTERNAL_APP", 0))
    if external_application == 0:
        os.environ["GUNICORN_WORKING_DIR"] = "/usr/src/app"
    elif external_application == 1:
        os.environ["GUNICORN_WORKING_DIR"] = "/usr/src/app"
    else:
        raise Exception("No external application found")

    if external_application == 0:
        click.echo("Starting cornflow")
        app = create_app(environment, cornflow_db_conn)
        with app.app_context():
            path = f"{os.path.dirname(cornflow.__file__)}/migrations"
            migrate = Migrate(app=app, db=db, directory=path)
            upgrade()
            access_init_command(verbose=False)
            if auth == 1 or auth == 0:
                create_user_with_role(
                    cornflow_admin_user,
                    cornflow_admin_email,
                    cornflow_admin_pwd,
                    "admin",
                    ADMIN_ROLE,
                    verbose=True,
                )
                # create cornflow service user
                create_user_with_role(
                    cornflow_service_user,
                    cornflow_service_email,
                    cornflow_service_pwd,
                    "serviceuser",
                    SERVICE_ROLE,
                    verbose=True,
                )
            register_deployed_dags_command(
                airflow_url, airflow_user, airflow_pwd, verbose=True
            )
            register_dag_permissions_command(open_deployment, verbose=True)
            update_schemas_command(airflow_url, airflow_user, airflow_pwd, verbose=True)

        # execute gunicorn application
        os.system(
            "/usr/local/bin/gunicorn -c python:cornflow.gunicorn \"cornflow.app:create_app('$FLASK_ENV')\""
        )

    elif external_application == 1:
        click.echo(f"Starting cornflow + {os.getenv('EXTERNAL_APP_MODULE')}")
        os.chdir("/usr/src/app")

        if register_key():
            prefix = "CUSTOM_SSH_"
            env_variables = {}
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    env_variables[key] = value

            for _, value in env_variables.items():
                register_ssh_host(value)

        os.system("$(command -v pip) install --user -r requirements.txt")
        time.sleep(5)
        sys.path.append("/usr/src/app")

        from importlib import import_module

        external_app = import_module(os.getenv("EXTERNAL_APP_MODULE"))
        app = external_app.create_wsgi_app(environment, cornflow_db_conn)
        with app.app_context():
            path = f"{os.path.dirname(external_app.__file__)}/migrations"
            migrate = Migrate(app=app, db=db, directory=path)
            upgrade()
            access_init_command(verbose=False)
            if auth == 1 or auth == 0:
                # create cornflow admin user
                create_user_with_role(
                    cornflow_admin_user,
                    cornflow_admin_email,
                    cornflow_admin_pwd,
                    "admin",
                    ADMIN_ROLE,
                    verbose=True,
                )
                # create cornflow service user
                create_user_with_role(
                    cornflow_service_user,
                    cornflow_service_email,
                    cornflow_service_pwd,
                    "serviceuser",
                    SERVICE_ROLE,
                    verbose=True,
                )
            register_deployed_dags_command(
                airflow_url, airflow_user, airflow_pwd, verbose=True
            )
            register_dag_permissions_command(open_deployment, verbose=True)
            update_schemas_command(airflow_url, airflow_user, airflow_pwd, verbose=True)

        os.system(
            f"/usr/local/bin/gunicorn -c python:cornflow.gunicorn "
            f"\"$EXTERNAL_APP_MODULE:create_wsgi_app('$FLASK_ENV')\""
        )

    else:
        raise Exception("No external application found")


def register_ssh_host(host):
    if host is not None:
        add_host = f"ssh-keyscan {host} >> /usr/src/app/.ssh/known_hosts"
        config_ssh_host = f"echo Host {host} >> /usr/src/app/.ssh/config"
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
