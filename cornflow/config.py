import os
from .shared.const import AUTH_DB, AUTH_LDAP


class MainEnvVars(object):
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))

    # LDAP configuration
    LDAP_HOST = os.getenv("LDAP_HOST")
    LDAP_BIND_DN = os.getenv("LDAP_BIND_DN")
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD")
    LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE")
    LDAP_USER_BASE = os.getenv("LDAP_USER_BASE")
    LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE")
    LDAP_USER_OBJECT_CLASS = os.getenv("LDAP_USER_OBJECT_CLASS")

    LDAP_GROUP_OBJECT_CLASS = os.getenv("LDAP_GROUP_OBJECT_CLASS")
    LDAP_GROUP_ATTRIBUTE = os.getenv("LDAP_GROUP_ATTRIBUTE")
    LDAP_GROUP_BASE = os.getenv("LDAP_GROUP_BASE")
    LDAP_GROUP_TO_ROLE_SERVICE = os.getenv("LDAP_GROUP_TO_ROLE_SERVICE")
    LDAP_GROUP_TO_ROLE_ADMIN = os.getenv("LDAP_GROUP_TO_ROLE_ADMIN")
    LDAP_GROUP_TO_ROLE_VIEWER = os.getenv("LDAP_GROUP_TO_ROLE_VIEWER")
    LDAP_GROUP_TO_ROLE_PLANNER = os.getenv("LDAP_GROUP_TO_ROLE_PLANNER")

    LDAP_PROTOCOL_VERSION = int(os.getenv("LDAP_PROTOCOL_VERSION", 3))
    LDAP_USE_TLS = os.getenv("LDAP_USE_TLS")


class Development(MainEnvVars):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True


class Testing(object):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    TESTING = True
    SECRET_KEY = "TESTINGSECRETKEY"
    SQLALCHEMY_DATABASE_URI = "sqlite:///cornflow_test.db"
    AIRFLOW_URL = "http://localhost:8080"
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    AIRFLOW_USER = "admin"
    AIRFLOW_PWD = "admin"
    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))

    # LDAP configuration
    LDAP_PROTOCOL_VERSION = 3
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "admin")
    LDAP_BIND_DN = "cn=admin,dc=example,dc=org"
    LDAP_USE_TLS = False
    LDAP_HOST = os.getenv("LDAP_HOST")
    LDAP_USERNAME_ATTRIBUTE = "cn"
    LDAP_USER_BASE = "ou=users,dc=example,dc=org"
    LDAP_EMAIL_ATTRIBUTE = "mail"
    LDAP_USER_OBJECT_CLASS = "inetOrgPerson"
    LDAP_GROUP_BASE = os.getenv("LDAP_GROUP_BASE")


class Production(MainEnvVars):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False


app_config = {"development": Development, "testing": Testing, "production": Production}
