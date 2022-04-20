import os
from apispec import APISpec
from cornflow_core.constants import AUTH_DB, PLANNER_ROLE
from apispec.ext.marshmallow import MarshmallowPlugin


class BaseDefaultConfig(object):
    """
    Base default configuration of a flask REST API
    """

    SERVICE_NAME = os.getenv("SERVICE_NAME")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{SERVICE_NAME.lower()}.db"
    )
    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))
    DEFAULT_ROLE = int(os.getenv("DEFAULT_ROLE", PLANNER_ROLE))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True

    # Planner users can access objects of other users (1) or not(0).
    USER_ACCESS_ALL_OBJECTS = os.getenv("USER_ACCESS_ALL_OBJECTS", 0)

    # LDAP configuration
    LDAP_HOST = os.getenv("LDAP_HOST", "ldap://openldap:389")
    LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "cn=admin,dc=example,dc=org")
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "admin")
    LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE", "cn")
    LDAP_USER_BASE = os.getenv("LDAP_USER_BASE", "ou=users,dc=example,dc=org")
    LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE", "mail")
    LDAP_USER_OBJECT_CLASS = os.getenv("LDAP_USER_OBJECT_CLASS", "inetOrgPerson")

    LDAP_GROUP_OBJECT_CLASS = os.getenv("LDAP_GROUP_OBJECT_CLASS", "posixGroup")
    LDAP_GROUP_ATTRIBUTE = os.getenv("LDAP_GROUP_ATTRIBUTE", "cn")
    LDAP_GROUP_BASE = os.getenv("LDAP_GROUP_BASE", "ou=groups,dc=example,dc=org")
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
        title=f"{SERVICE_NAME} API docs",
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
