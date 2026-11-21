import os
from cornflow.shared.const import (
    AUTH_DB,
    PLANNER_ROLE,
    AUTH_OID,
    SIGNUP_WITH_NO_AUTH,
    OID_OTHER,
    AIRFLOW_BACKEND,
    DATABRICKS_BACKEND,
    USER_ACCESS_ALL_OBJECTS_NO,
)
from cornflow.shared.security_levels import (
    SECURITY_LEVEL_ENV_VAR,
    apply_security_settings,
    resolve_security_settings,
)
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

# The security settings (CORNFLOW_SECURITY_LEVEL and the variables of the
# inventory in cornflow/shared/security_levels.py) are resolved once, when this
# module is imported. Invalid values never break the import: they are recorded
# in SECURITY_LEVEL_ERROR / SECURITY_CONFIG_ERRORS and create_app refuses to
# start with them.
_SECURITY = resolve_security_settings(os.environ)
# Testing does not depend on the environment: level 3 defaults.
_TESTING_SECURITY = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: "3"})


class DefaultConfig(object):
    """
    Default configuration class
    """

    APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "/")
    EXTERNAL_APP = int(os.getenv("EXTERNAL_APP", 0))
    SERVICE_NAME = os.getenv("SERVICE_NAME", "Cornflow")
    SECRET_TOKEN_KEY = os.getenv("SECRET_KEY")
    SECRET_BI_KEY = os.getenv("SECRET_BI_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow.db")

    AUTH_TYPE = int(os.getenv("AUTH_TYPE", AUTH_DB))
    DEFAULT_ROLE = int(os.getenv("DEFAULT_ROLE", PLANNER_ROLE))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    TESTING = True
    LOG_LEVEL = int(os.getenv("LOG_LEVEL", 20))
    CORNFLOW_SERVICE_USER = os.getenv("CORNFLOW_SERVICE_USER", "service_user")

    # To change the tasks backend used by cornflow to solve the optimization models
    CORNFLOW_BACKEND = int(os.getenv("CORNFLOW_BACKEND", AIRFLOW_BACKEND))

    # AIRFLOW config
    AIRFLOW_URL = os.getenv("AIRFLOW_URL")
    AIRFLOW_USER = os.getenv("AIRFLOW_USER")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD")

    # DATABRICKS config
    DATABRICKS_URL = os.getenv("DATABRICKS_HOST")
    DATABRICKS_AUTH_SECRET = os.getenv("DATABRICKS_CLIENT_SECRET")
    DATABRICKS_TOKEN_ENDPOINT = os.getenv("DATABRICKS_TOKEN_ENDPOINT")
    DATABRICKS_EP_CLUSTERS = os.getenv("DATABRICKS_EP_CLUSTERS")
    DATABRICKS_CLIENT_ID = os.getenv("DATABRICKS_CLIENT_ID")
    DATABRICKS_HEALTH_PATH = os.getenv("DATABRICKS_HEALTH_PATH", "default path")

    # Open deployment (all dags accessible to all users)
    OPEN_DEPLOYMENT = os.getenv("OPEN_DEPLOYMENT", 1)

    # Planner users can access objects of other users (1) or not(0).
    USER_ACCESS_ALL_OBJECTS = os.getenv(
        "USER_ACCESS_ALL_OBJECTS", USER_ACCESS_ALL_OBJECTS_NO
    )

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

    # OpenID Connect configuration
    OID_PROVIDER = os.getenv("OID_PROVIDER")
    OID_PROVIDER_TYPE = int(os.getenv("OID_PROVIDER_TYPE", OID_OTHER))
    OID_EXPECTED_AUDIENCE = os.getenv("OID_EXPECTED_AUDIENCE")

    # APISPEC:
    APISPEC_SPEC = APISpec(
        title="cornflow API docs",
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

    # Execution files
    EXECUTION_FILES = int(os.getenv("EXECUTION_FILES", 0))
    execution_files_path = os.path.join(os.getcwd(), "execution_files")
    EXECUTION_FILES_PATH = os.getenv("EXECUTION_FILES_PATH", execution_files_path)
    # Cleanup frequency (in days). By default, execution files that are older than 90 days will be deleted.
    #    If 0: no executions files will ever be deleted.
    EXECUTION_FILES_CLEANUP_FREQUENCY = int(
        os.getenv("EXECUTION_FILES_CLEANUP_FREQUENCY", 90)
    )

    # Return the standard rate-limit headers on responses
    RATELIMIT_HEADERS_ENABLED = True


apply_security_settings(DefaultConfig, _SECURITY)


class Development(DefaultConfig):
    """
    Configuration class for development
    """

    ENV = "development"


class Testing(DefaultConfig):
    """
    Configuration class for testing
    """

    ENV = "testing"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = True
    PROPAGATE_EXCEPTIONS = True
    SECRET_TOKEN_KEY = "TESTINGSECRETKEY_TESTINGSECRETKEY_32B"
    SECRET_BI_KEY = "THISISANOTHERKEY_THISISANOTHERKEY_32B"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cornflow_test.db")
    AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8080")
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
    AIRFLOW_PWD = os.getenv("AIRFLOW_PWD", "admin")
    OPEN_DEPLOYMENT = 1
    LOG_LEVEL = int(os.getenv("LOG_LEVEL", 10))

    # Test-suite deviations from the level 3 defaults applied below
    CORS_ORIGINS = "*"
    DOCS_ENABLED = 1
    HSTS_ENABLED = 0
    # MFA is not required for the generic test suite. Specific MFA tests
    # activate it explicitly.
    MFA_REQUIRED = 0
    # Rate limiting is disabled for the generic test suite (which makes many
    # rapid login calls). Specific rate-limit tests enable it explicitly.
    RATELIMIT_ENABLED = 0
    # Low bcrypt work factor to keep the test suite fast
    BCRYPT_LOG_ROUNDS = 4
    SIGNUP_ACTIVATED = SIGNUP_WITH_NO_AUTH


apply_security_settings(Testing, _TESTING_SECURITY)


class TestingDatabricks(Testing):
    CORNFLOW_BACKEND = DATABRICKS_BACKEND


class TestingRateLimit(Testing):
    """
    Configuration class for the rate-limiting tests (the feature is off in
    the base testing config so the rest of the suite is not throttled).
    """

    RATELIMIT_ENABLED = 1
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_LOGIN = "3 per minute"
    RATELIMIT_RECOVER = "2 per hour"


class TestingOpenAuth(Testing):
    """
    Configuration class for testing some edge cases with Open Auth login
    """

    AUTH_TYPE = AUTH_OID
    OID_PROVIDER = "https://test-provider.example.com"
    OID_EXPECTED_AUDIENCE = "test-audience-id"


class TestingApplicationRoot(Testing):
    """
    Configuration class for testing with application root
    """

    APPLICATION_ROOT = "/test"


class Production(DefaultConfig):
    """
    Configuration class for production
    """

    ENV = "production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    # needs to be on to avoid getting only 500 codes:
    # and https://medium.com/@johanesriandy/flask-error-handler-not-working-on-production-mode-3adca4c7385c
    PROPAGATE_EXCEPTIONS = True
    # CORS_ORIGINS, DOCS_ENABLED and HSTS_ENABLED are not set here: they depend
    # on CORNFLOW_SECURITY_LEVEL, whatever FLASK_ENV is.


app_config = {
    "development": Development,
    "testing": Testing,
    "production": Production,
    "testing-oauth": TestingOpenAuth,
    "testing-root": TestingApplicationRoot,
    "testing-databricks": TestingDatabricks,
    "testing-ratelimit": TestingRateLimit,
}
