# Airflow init script for Dockerfile ENTRYPOINT
from logging import error
import os
import sys
from cryptography.fernet import Fernet
import time

###################################
# Global defaults and back-compat #
###################################
# Airflow global default
# Get env config
global_env_vars = [
("AIRFLOW_HOME", "/usr/local/airflow"), 
("EXECUTOR", "Sequential"), 
("AIRFLOW__CORE__LOAD_EXAMPLES", "0"),
("AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION", "0"),
("AIRFLOW__API__AUTH_BACKEND", "airflow.api.auth.backend.basic_auth"),
("AIRFLOW__CORE__FERNET_KEY", Fernet.generate_key().decode()),
("AIRFLOW_USER", "admin"),
("AIRFLOW_FIRSTNAME", "admin"),
("AIRFLOW_LASTNAME", "admin"),
("AIRFLOW_ROLE", "Admin"),
("AIRFLOW_PWD", "admin"),
("AIRFLOW_USER_EMAIL", "admin@example.com"),
("CORNFLOW_SERVICE_USER", "serviceuser@cornflow.com"),
("CORNFLOW_SERVICE_PWD", "servicecornflow1234"),
("AIRFLOW_LDAP_ENABLE", "False")
]
# update environ set
for name, default in global_env_vars:
    os.environ[name] = os.getenv(name, default)

# Set this local var for use later
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME")
AIRFLOW_USER = os.getenv("AIRFLOW_USER")
AIRFLOW_FIRSTNAME = os.getenv("AIRFLOW_FIRSTNAME")
AIRFLOW_LASTNAME = os.getenv("AIRFLOW_LASTNAME")
AIRFLOW_ROLE = os.getenv("AIRFLOW_ROLE")
AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
AIRFLOW_USER_EMAIL = os.getenv("AIRFLOW_USER_EMAIL")
CORNFLOW_SERVICE_USER = os.getenv("CORNFLOW_SERVICE_USER")
CORNFLOW_SERVICE_PWD = os.getenv("CORNFLOW_SERVICE_PWD")
AIRFLOW_LDAP_ENABLE = os.getenv("AIRFLOW_LDAP_ENABLE")

# Config execution type for airflow
AIRFLOW__CORE__EXECUTOR = os.getenv("EXECUTOR")
os.environ["AIRFLOW__CORE__EXECUTOR"] = f"{AIRFLOW__CORE__EXECUTOR}Executor"

# Add ssh key for install packages inside workers
CUSTOM_SSH_HOST = os.getenv("CUSTOM_SSH_HOST")
if os.path.isfile("/usr/local/airflow/.ssh/id_rsa") and CUSTOM_SSH_HOST is not None:
    ADD_KEY = "chmod 0600 /usr/local/airflow/.ssh/id_rsa && ssh-add /usr/local/airflow/.ssh/id_rsa"
    ADD_HOST = f"ssh-keyscan {CUSTOM_SSH_HOST} >> /usr/local/airflow/.ssh/known_hosts"
    CONFIG_SSH_HOST = f"echo Host {CUSTOM_SSH_HOST} > /usr/local/airflow/.ssh/config"
    CONFIG_SSH_KEY = 'echo "    IdentityFile /usr/local/airflow/.ssh/id_rsa" >> /usr/local/airflow/.ssh/config'
    os.system(ADD_KEY)
    os.system(ADD_HOST)
    os.system(CONFIG_SSH_HOST)
    os.system(CONFIG_SSH_KEY)

# Install custom python package if requirements.txt is present
if os.path.isfile("/requirements.txt"):
    os.system("$(command -v pip) install --user -r /requirements.txt")

# Make SQL connention
if os.getenv("AIRFLOW__CORE__SQL_ALCHEMY_CONN") is None:
    # Default values corresponding to the default compose files
    AIRFLOW_DB_HOST = os.getenv("AIRFLOW_DB_HOST", "airflow_db")
    AIRFLOW_DB_PORT = os.getenv("AIRFLOW_DB_PORT", "5432")
    AIRFLOW_DB_USER = os.getenv("AIRFLOW_DB_USER", "airflow")
    AIRFLOW_DB_PWD = os.getenv("AIRFLOW_DB_PWD", "airflow")
    AIRFLOW_DB = os.getenv("AIRFLOW_DB", "airflow")

    AIRFLOW__CORE__SQL_ALCHEMY_CONN = f"postgresql+psycopg2://{AIRFLOW_DB_USER}:{AIRFLOW_DB_PWD}@{AIRFLOW_DB_HOST}:{AIRFLOW_DB_PORT}/{AIRFLOW_DB}"
    os.environ["AIRFLOW__CORE__SQL_ALCHEMY_CONN"] = AIRFLOW__CORE__SQL_ALCHEMY_CONN

    # Check if the user has provided explicit Airflow configuration for the broker's connection to the database
    if os.getenv("AIRFLOW__CORE__EXECUTOR") == "CeleryExecutor":
        AIRFLOW__CELERY__RESULT_BACKEND = f"db+postgresql://{AIRFLOW_DB_USER}:{AIRFLOW_DB_PWD}@{AIRFLOW_DB_HOST}:{AIRFLOW_DB_PORT}/{AIRFLOW_DB}"
        os.environ["AIRFLOW__CELERY__RESULT_BACKEND"] = AIRFLOW__CELERY__RESULT_BACKEND

# CeleryExecutor drives the need for a Celery broker, here Redis is used
if os.getenv("AIRFLOW__CORE__EXECUTOR") == "CeleryExecutor":
    # Check if the user has provided explicit Airflow configuration concerning the broker
    if os.getenv("AIRFLOW__CELERY__BROKER_URL") is None:
        # Default values corresponding to the default compose files
        REDIS_PROTO = os.getenv("REDIS_PROTO", "redis://")
        REDIS_HOST = os.getenv("REDIS_HOST", "redis")
        REDIS_PORT = os.getenv("REDIS_PORT", "6379")
        REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        REDIS_DBNUM = os.getenv("REDIS_DBNUM", "1")

    # When Redis is secured by basic auth, it does not handle the username part of basic auth, only a token
    if REDIS_PASSWORD is not None:
        REDIS_PREFIX = f":{REDIS_PASSWORD}@"
    else:
        REDIS_PREFIX = None

    AIRFLOW__CELERY__BROKER_URL = (
        f"{REDIS_PROTO}{REDIS_PREFIX}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DBNUM}"
    )
    os.environ["AIRFLOW__CELERY__BROKER_URL"] = AIRFLOW__CELERY__BROKER_URL

# Make cornflow connection for response from workers
if os.getenv("AIRFLOW_CONN_CF_URI") is None:
    # Default values corresponding to the default compose files
    CORNFLOW_HOST = os.getenv("CORNFLOW_HOST", "cornflow")
    CORNFLOW_PORT = os.getenv("CORNFLOW_PORT", "5000")
    os.environ["CORNFLOW_HOST"] = CORNFLOW_HOST
    os.environ["CORNFLOW_PORT"] = CORNFLOW_PORT
    # Make the uri connection to get back response from airflow
    AIRFLOW_CONN_CF_URI = f"cornflow://{CORNFLOW_SERVICE_USER}:{CORNFLOW_SERVICE_PWD}@{CORNFLOW_HOST}:{CORNFLOW_PORT}"
    os.environ["AIRFLOW_CONN_CF_URI"] = AIRFLOW_CONN_CF_URI

# Check LDAP parameters for active directory
if os.getenv("AIRFLOW_LDAP_ENABLE") == "True":
    # Rename webserver config file for using LDAP
    os.rename(
        f"{AIRFLOW_HOME}/webserver_ldap.py", f"{AIRFLOW_HOME}/webserver_config.py"
    )
    # Update LDAP env values
    os.environ["AIRFLOW_LDAP_URI"] = os.getenv("AIRFLOW_LDAP_URI", "ldap://openldap:389")
    os.environ["AIRFLOW_LDAP_SEARCH"] = os.getenv("AIRFLOW_LDAP_SEARCH", "ou=users,dc=example,dc=org")
    os.environ["AIRFLOW_LDAP_BIND_USER"] = os.getenv(
        "AIRFLOW_LDAP_BIND_USER", "cn=admin,dc=example,dc=org"
    )
    os.environ["AIRFLOW_LDAP_BIND_PASSWORD"] = os.getenv("AIRFLOW_LDAP_BIND_PASSWORD", "admin")
    os.environ["AIRFLOW_LDAP_UID_FIELD"] = os.getenv("AIRFLOW_LDAP_UID_FIELD", "cn")
    os.environ["AIRFLOW_LDAP_ROLE_MAPPING_ADMIN"] = os.getenv(
        "AIRFLOW_LDAP_ROLE_MAPPING_ADMIN",
        "cn=administrators,ou=groups,dc=example,dc=org",
    )
    os.environ["AIRFLOW_LDAP_ROLE_MAPPING_OP"] = os.getenv(
        "AIRFLOW_LDAP_ROLE_MAPPING_OP", "cn=services,ou=groups,dc=example,dc=org"
    )
    os.environ["AIRFLOW_LDAP_ROLE_MAPPING_PUBLIC"] = os.getenv(
        "AIRFLOW_LDAP_ROLE_MAPPING_PUBLIC", "cn=viewers,ou=groups,dc=example,dc=org"
    )
    os.environ["AIRFLOW_LDAP_ROLE_MAPPING_VIEWER"] = os.getenv(
        "AIRFLOW_LDAP_ROLE_MAPPING_VIEWER", "cn=planners,ou=groups,dc=example,dc=org"
    )
    os.environ["AIRFLOW_LDAP_GROUP_FIELD"] = os.getenv("AIRFLOW_LDAP_GROUP_FIELD", "memberUid")
    # Special condition for using TLS
    if os.getenv("AIRFLOW_LDAP_USE_TLS") == "True" and os.getenv("AIRFLOW_LDAP_TLS_CA_CERTIFICATE") is None:
        sys.exit(
            "FATAL: if you set AIRFLOW_LDAP_USE_TLS you must also set AIRFLOW_LDAP_TLS_CA_CERTIFICATE"
        )

# Entrypoint of airflow services depends on command given by arg       
def airflowsvc(afsvc):
    if afsvc == "webserver":
        os.system("airflow db init")
        # Create user only if using AUTH_DB
        if os.getenv("AIRFLOW_LDAP_ENABLE") != "True":
            os.system(
                f"airflow users create --username {AIRFLOW_USER} --firstname {AIRFLOW_FIRSTNAME} --lastname {AIRFLOW_LASTNAME} --role {AIRFLOW_ROLE} --password {AIRFLOW_PWD} --email {AIRFLOW_USER_EMAIL}"
            )
        if (
            os.getenv("AIRFLOW__CORE__EXECUTOR") == "LocalExecutor"
            or os.getenv("AIRFLOW__CORE__EXECUTOR") == "SequentialExecutor"
        ):
            # With the "Local" and "Sequential" executors it should all run in one container.
            os.system["airflow scheduler &"]
        os.system("airflow webserver")
    if afsvc == "worker":
        time.sleep(10)
        os.system(f"airflow celery {afsvc}")
    if afsvc == "scheduler":
        time.sleep(10)
        os.system(f"airflow {afsvc}")
    if afsvc == "flower":
        time.sleep(10)
        os.system(f"airflow celery {afsvc} --basic-auth={AIRFLOW_USER}:{AIRFLOW_PWD}")
    else:
        os.system("airflow version")


if __name__ == "__main__":
    airflowsvc(sys.argv[1])
