# Cornflow init script for Dockerfile ENTRYPOINT
from logging import error
import subprocess
import os
import sys
from cryptography.fernet import Fernet
from flask_migrate import Migrate, upgrade
from cornflow.shared.const import ADMIN_ROLE, AUTH_DB, SERVICE_ROLE
from cornflow.app import create_app, db
from cornflow.commands.commands import AccessInitialization, create_user_with_role

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
    "postgres://"
    + CORNFLOW_DB_USER
    + ":"
    + CORNFLOW_DB_PASSWORD
    + "@"
    + CORNFLOW_DB_HOST
    + ":"
    + CORNFLOW_DB_PORT
    + "/"
    + CORNFLOW_DB,
)
os.environ["DATABASE_URL"] = CORNFLOW_DB_CONN

# Platform auth config and service users
AUTH = int(os.getenv("AUTH_TYPE", AUTH_DB))
CORNFLOW_ADMIN_USER = os.getenv("CORNFLOW_ADMIN_USER", "cornflow_admin")
CORNFLOW_ADMIN_EMAIL = os.getenv("CORNFLOW_ADMIN_EMAIL", "cornflow_admin@cornflow.com")
CORNFLOW_ADMIN_PWD = os.getenv("CORNFLOW_ADMIN_PWD", "cornflowadmin1234")
CORNFLOW_SERVICE_USER = os.getenv("CORNFLOW_SERVICE_USER", "service_user")
CORNFLOW_SERVICE_EMAIL = os.getenv(
    "CORNFLOW_SERVICE_EMAIL", "service_user@cornflow.com"
)
CORNFLOW_SERVICE_PWD = os.getenv("CORNFLOW_SERVICE_PWD", "serviceuser1234")

# Cornflow logging and storage config
CORNFLOW_LOGGING = os.getenv("CORNFLOW_LOGGING", "console")
os.environ["CORNFLOW_LOGGING"] = CORNFLOW_LOGGING

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
            "cat > /etc/logrotate.d/cornflow <<EOF\n" + conf + "\nEOF", shell=True
        )
        out_logrotate = logrotate.stdout
        print(out_logrotate)

    except (error):
        print(error)

# make initdb, access control and/or migrations
app = create_app(ENV,CORNFLOW_DB_CONN)
with app.app_context():
    migrate = Migrate(app=app, db=db)
    upgrade()
    AccessInitialization.run(self=AccessInitialization, verbose=1)
    # create user if auth type is db
    if AUTH == 1:
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

# execute gunicorn application
os.system(
    "/usr/local/bin/gunicorn -c cornflow/gunicorn.py \"cornflow:create_app('$FLASK_ENV')\""
)
