import os
from .shared.const import AUTH_DB
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin


class DefaultConfig(object):
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow.db")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True

    # LDAP configuration
    LDAP_HOST = os.getenv("LDAP_HOST","ldap://openldap:389")
    LDAP_BIND_DN = os.getenv("LDAP_BIND_DN","cn=admin,dc=example,dc=org")
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD","admin")
    LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE","cn")
    LDAP_USER_BASE = os.getenv("LDAP_USER_BASE","ou=users,dc=example,dc=org")
    LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE","mail")
    LDAP_USER_OBJECT_CLASS = os.getenv("LDAP_USER_OBJECT_CLASS","inetOrgPerson")

    LDAP_GROUP_OBJECT_CLASS = os.getenv("LDAP_GROUP_OBJECT_CLASS","posixGroup")
    LDAP_GROUP_ATTRIBUTE = os.getenv("LDAP_GROUP_ATTRIBUTE","cn")
    LDAP_GROUP_BASE = os.getenv("LDAP_GROUP_BASE","ou=groups,dc=example,dc=org")
    LDAP_GROUP_TO_ROLE_SERVICE = os.getenv("LDAP_GROUP_TO_ROLE_SERVICE","service")
    LDAP_GROUP_TO_ROLE_ADMIN = os.getenv("LDAP_GROUP_TO_ROLE_ADMIN","administrators")
    LDAP_GROUP_TO_ROLE_VIEWER = os.getenv("LDAP_GROUP_TO_ROLE_VIEWER","viewers")
    LDAP_GROUP_TO_ROLE_PLANNER = os.getenv("LDAP_GROUP_TO_ROLE_PLANNER","planners")

    LDAP_PROTOCOL_VERSION = int(os.getenv("LDAP_PROTOCOL_VERSION", 3))
    LDAP_USE_TLS = os.getenv("LDAP_USE_TLS","False")

    # APISPEC:
    APISPEC_SPEC = APISpec(
        title="Cornflow API docs",
        version="v1",
        plugins=[MarshmallowPlugin()],
        openapi_version="2.0.0",
    )
    APISPEC_SWAGGER_URL = "/swagger/"
    APISPEC_SWAGGER_UI_URL = "/swagger-ui/"

    # compress config
    COMPRESS_REGISTER = False


class Development(DefaultConfig):
    """ """


class Testing(DefaultConfig):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = True
    PROPAGATE_EXCEPTIONS = True
    SECRET_KEY = "TESTINGSECRETKEY"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow_test.db")
    AIRFLOW_URL = "http://localhost:8080"
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    AIRFLOW_USER = "admin"
    AIRFLOW_PWD = "admin"


class Production(DefaultConfig):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    # needs to be on to avoid getting only 500 codes:
    # and https://medium.com/@johanesriandy/flask-error-handler-not-working-on-production-mode-3adca4c7385c
    PROPAGATE_EXCEPTIONS = True


app_config = {"development": Development, "testing": Testing, "production": Production}
