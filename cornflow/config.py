import os


class Development(object):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
    CORNFLOW_LDAP_ENABLE = os.getenv("CORNFLOW_LDAP_ENABLE")

    if CORNFLOW_LDAP_ENABLE:
        LDAP_PROTOCOL_VERSION = os.getenv("LDAP_PROTOCOL_VERSION")
        LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD")
        LDAP_BIND_DN = os.getenv("LDAP_BIND_DN")
        LDAP_USE_TLS = os.getenv("LDAP_USE_TLS")
        LDAP_HOST = os.getenv("LDAP_HOST")
        LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE")
        LDAP_USER_BASE = os.getenv("LDAP_USER_BASE")
        LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE")


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
    CORNFLOW_LDAP_ENABLE = False
    if CORNFLOW_LDAP_ENABLE:
        LDAP_PROTOCOL_VERSION = 3
        LDAP_BIND_PASSWORD = "adminldap"
        LDAP_BIND_DN = "cn=admin,dc=example,dc=org"
        LDAP_USE_TLS = False
        LDAP_HOST = "ldap://35.205.18.159:389"
        LDAP_USERNAME_ATTRIBUTE = "cn"
        LDAP_USER_BASE = "ou=user,dc=example,dc=org"
        LDAP_EMAIL_ATTRIBUTE = "mail"
        LDAP_USER_OBJECT_CLASS = "inetOrgPerson"


class Production(object):
    """ """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")
    CORNFLOW_LDAP_ENABLE = os.getenv("CORNFLOW_LDAP_ENABLE")
    if CORNFLOW_LDAP_ENABLE:
        LDAP_PROTOCOL_VERSION = os.getenv("LDAP_PROTOCOL_VERSION")
        LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD")
        LDAP_BIND_DN = os.getenv("LDAP_BIND_DN")
        LDAP_USE_TLS = os.getenv("LDAP_USE_TLS")
        LDAP_HOST = os.getenv("LDAP_HOST")
        LDAP_USERNAME_ATTRIBUTE = os.getenv("LDAP_USERNAME_ATTRIBUTE")
        LDAP_USER_BASE = os.getenv("LDAP_USER_BASE")
        LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE")


app_config = {"development": Development, "testing": Testing, "production": Production}
