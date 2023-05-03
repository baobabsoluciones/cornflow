import os
from .shared.const import AUTH_DB, PLANNER_ROLE
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin


class DefaultConfig(object):
    SERVICE_NAME = os.getenv("SERVICE_NAME", "Cornflow")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow.db")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))
    DEFAULT_ROLE = int(os.getenv("DEFAULT_ROLE", PLANNER_ROLE))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True
    LOG_LEVEL = int(os.getenv("LOG_LEVEL", 20))
    SIGNUP_ACTIVATED = int(os.getenv("SIGNUP_ACTIVATED", 1))
    CORNFLOW_SERVICE_USER = os.getenv("CORNFLOW_SERVICE_USER", "service_user")

    # Open deployment (all dags accessible to all users)
    OPEN_DEPLOYMENT = os.getenv("OPEN_DEPLOYMENT", 1)

    # Planner users can access objects of other users (1) or not(0).
    USER_ACCESS_ALL_OBJECTS = os.getenv("USER_ACCESS_ALL_OBJECTS", 0)

    # LDAP configuration
    LDAP_HOST = os.getenv("LDAP_HOST", "ldap://openldap:389")
    LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "cn=admin,dc=example,dc=org")
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "admin")
    LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE", "cn")
    LDAP_USER_BASE = os.getenv("LDAP_USER_BASE", "ou=users,dc=example,dc=org")
    LDAP_SERVICE_BASE = os.getenv("LDAP_SERVICE_BASE", LDAP_USER_BASE)
    LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE", "mail")
    LDAP_USER_OBJECT_CLASS = os.getenv("LDAP_USER_OBJECT_CLASS", "inetOrgPerson")
    LDAP_GROUP_OBJECT_CLASS = os.getenv("LDAP_GROUP_OBJECT_CLASS", "groupOfNames")
    LDAP_GROUP_ATTRIBUTE = os.getenv("LDAP_GROUP_ATTRIBUTE", "cn")
    LDAP_GROUP_BASE = os.getenv("LDAP_GROUP_BASE", "dc=example,dc=org")
    LDAP_GROUP_TO_ROLE_SERVICE = os.getenv("LDAP_GROUP_TO_ROLE_SERVICE", "service")
    LDAP_GROUP_TO_ROLE_ADMIN = os.getenv("LDAP_GROUP_TO_ROLE_ADMIN", "administrators")
    LDAP_GROUP_TO_ROLE_VIEWER = os.getenv("LDAP_GROUP_TO_ROLE_VIEWER", "viewers")
    LDAP_GROUP_TO_ROLE_PLANNER = os.getenv("LDAP_GROUP_TO_ROLE_PLANNER", "planners")

    LDAP_PROTOCOL_VERSION = int(os.getenv("LDAP_PROTOCOL_VERSION", 3))
    LDAP_USE_TLS = os.getenv("LDAP_USE_TLS", "False")

    # OpenID login -> Default Azure
    OID_PROVIDER = os.getenv("OID_PROVIDER", 0)
    OID_CLIENT_ID = os.getenv("OID_CLIENT_ID")
    OID_TENANT_ID = os.getenv("OID_TENANT_ID")
    OID_ISSUER = os.getenv("OID_ISSUER")

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

    # Email server
    SERVICE_EMAIL_ADDRESS = os.getenv("SERVICE_EMAIL_ADDRESS", None)
    SERVICE_EMAIL_PASSWORD = os.getenv("SERVICE_EMAIL_PASSWORD", None)
    SERVICE_EMAIL_SERVER = os.getenv("SERVICE_EMAIL_SERVER", None)
    SERVICE_EMAIL_PORT = os.getenv("SERVICE_EMAIL_PORT", None)

    # Alarms endpoints
    ALARMS_ENDPOINTS = os.getenv("CF_ALARMS_ENDPOINT", 0)


class Development(DefaultConfig):

    """ """

    ENV = "development"


class Testing(DefaultConfig):
    """ """

    ENV = "testing"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = True
    PROPAGATE_EXCEPTIONS = True
    SECRET_KEY = "TESTINGSECRETKEY"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow_test.db")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8080")
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD", "admin")
    OPEN_DEPLOYMENT = 1
    LOG_LEVEL = int(os.getenv("LOG_LEVEL", 10))


class Production(DefaultConfig):
    """ """

    ENV = "production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    # needs to be on to avoid getting only 500 codes:
    # and https://medium.com/@johanesriandy/flask-error-handler-not-working-on-production-mode-3adca4c7385c
    PROPAGATE_EXCEPTIONS = True


app_config = {"development": Development, "testing": Testing, "production": Production}
