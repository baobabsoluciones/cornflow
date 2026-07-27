import os
from cornflow.shared.const import (
    AUTH_DB,
    PLANNER_ROLE,
    AUTH_OID,
    SIGNUP_WITH_AUTH,
    SIGNUP_WITH_NO_AUTH,
    OID_OTHER,
    AIRFLOW_BACKEND,
    DATABRICKS_BACKEND,
    USER_ACCESS_ALL_OBJECTS_NO,
    DEFAULT_PWD_MIN_LENGTH,
    DEFAULT_PWD_MIN_ZXCVBN_SCORE,
    DEFAULT_PWD_HISTORY_SIZE,
    DEFAULT_PWD_MAX_SIMILARITY,
    DEFAULT_PWD_ROTATION_TIME,
)
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin


def _env_int_floor(name: str, default: int, floor: int) -> int:
    """
    Reads an integer environment variable enforcing a security floor: the
    resulting value can never be lower than `floor`, so a tampered
    environment can not weaken the policy below the minimum threshold.
    """
    try:
        value = int(os.getenv(name, default))
    except (TypeError, ValueError):
        value = default
    return max(value, floor)


def _env_int_ceiling(name: str, default: int, ceiling: int) -> int:
    """
    Reads an integer environment variable enforcing a security ceiling: the
    resulting value can never be higher than `ceiling` (used where larger
    values weaken security, e.g. token lifetimes or lockout attempts).
    """
    try:
        value = int(os.getenv(name, default))
    except (TypeError, ValueError):
        value = default
    return min(value, ceiling)


def _env_float_ceiling(name: str, default: float, ceiling: float) -> float:
    """
    Float version of :func:`_env_int_ceiling`.
    """
    try:
        value = float(os.getenv(name, default))
    except (TypeError, ValueError):
        value = default
    return min(value, ceiling)


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
    # bcrypt work factor for password hashing (Flask-Bcrypt reads this when
    # generate_password_hash is called without an explicit rounds argument).
    # Floor of 12 as recommended by CCN-STIC-807 for the employed hashing.
    BCRYPT_LOG_ROUNDS = _env_int_floor("BCRYPT_LOG_ROUNDS", 12, 12)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DEBUG = True
    TESTING = True
    LOG_LEVEL = int(os.getenv("LOG_LEVEL", 20))
    SIGNUP_ACTIVATED = int(os.getenv("SIGNUP_ACTIVATED", SIGNUP_WITH_AUTH))
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
    # If service user is allowed to log with username and password
    SERVICE_USER_ALLOW_PASSWORD_LOGIN = int(
        os.getenv("SERVICE_USER_ALLOW_PASSWORD_LOGIN", 1)
    )

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

    # The security-related values below read the environment but are clamped
    # to a floor or a ceiling, so a compromised or misconfigured environment
    # can not weaken the policy below the CCN-STIC-807 minimum thresholds.

    # Token duration in hours (ceiling: 24). Used for the legacy single
    # session token (service users, or when refresh tokens are disabled) and
    # as the fallback session lifetime.
    TOKEN_DURATION = _env_float_ceiling("TOKEN_DURATION", 8, 24)

    # Refresh-token sessions (ENS op.acc — session management). When enabled
    # (default), an interactive login returns a short-lived ACCESS token plus
    # a REFRESH token; the client exchanges the refresh token for new access
    # tokens at /token/refresh/ while active. This gives a sliding inactivity
    # timeout (Model B) with a hard absolute cap, on top of a stateful,
    # revocable session store. Service users keep the single long-lived token
    # (they should use API keys for automation).
    REFRESH_TOKEN_ENABLED = int(os.getenv("REFRESH_TOKEN_ENABLED", 1))
    # Access-token lifetime in minutes (ceiling: 60). Short so revocation and
    # inactivity take effect quickly.
    ACCESS_TOKEN_DURATION_MINUTES = _env_int_ceiling(
        "ACCESS_TOKEN_DURATION_MINUTES", 15, 60
    )
    # Sliding inactivity window in minutes (ceiling: 720 / 12 h): a session
    # with no refresh for longer than this is closed and requires re-login.
    REFRESH_TOKEN_INACTIVITY_MINUTES = _env_int_ceiling(
        "REFRESH_TOKEN_INACTIVITY_MINUTES", 30, 720
    )
    # Absolute maximum session lifetime in hours (ceiling: 24): no session,
    # however active, lives longer than this before a full re-login.
    REFRESH_TOKEN_ABSOLUTE_HOURS = _env_int_ceiling(
        "REFRESH_TOKEN_ABSOLUTE_HOURS", 12, 24
    )

    # BI token lifetime in days (never-expiring BI tokens are not allowed).
    # Ceiling of 365 days; regenerate with `cornflow users bi_token`.
    BI_TOKEN_DURATION_DAYS = _env_int_ceiling("BI_TOKEN_DURATION_DAYS", 90, 365)

    # Personal API key (alternative long-lived credential to the session JWT)
    # If 0, personal API key generation is disabled on this deployment.
    PERSONAL_TOKEN_ENABLED = int(os.getenv("PERSONAL_TOKEN_ENABLED", 1))
    # API key lifetime in days (default 1 year, ceiling 2 years)
    API_KEY_DURATION_DAYS = _env_int_ceiling("API_KEY_DURATION_DAYS", 365, 730)
    # Require a fresh TOTP (step-up) when an MFA-enabled user generates an
    # API key through the API/UI. The CLI path is exempt (machine access).
    API_KEY_STEPUP_TOTP = int(os.getenv("API_KEY_STEPUP_TOTP", 1))
    # Rotation grace window in minutes: after generating a new API key the
    # previous one keeps working for this long, so a key wired into running
    # automation can be replaced without a gap (generate, then redeploy).
    # 0 disables the grace (the previous key dies immediately). Ceiling 1 day.
    API_KEY_ROTATION_GRACE_MINUTES = _env_int_ceiling(
        "API_KEY_ROTATION_GRACE_MINUTES", 60, 1440
    )

    # Expiry notifications for personal API keys. A daily run of
    # `cornflow tokens notify-expiry` emails the key owner and the platform
    # administrators when the key has this many days left or fewer.
    TOKEN_EXPIRY_NOTIFICATIONS_ENABLED = int(
        os.getenv("TOKEN_EXPIRY_NOTIFICATIONS_ENABLED", 1)
    )
    TOKEN_EXPIRY_NOTIFICATION_DAYS = os.getenv(
        "TOKEN_EXPIRY_NOTIFICATION_DAYS", "30,7,3,2,1"
    )

    # Password rotation time in days (ceiling: 365)
    PWD_ROTATION_TIME = _env_int_ceiling(
        "PWD_ROTATION_TIME", DEFAULT_PWD_ROTATION_TIME, 365
    )

    # Password policy (CCN-STIC-807 hardening). Defaults live in shared/const.py.
    # Minimum password length (floor: default)
    PWD_MIN_LENGTH = _env_int_floor(
        "PWD_MIN_LENGTH", DEFAULT_PWD_MIN_LENGTH, DEFAULT_PWD_MIN_LENGTH
    )
    # Minimum zxcvbn strength score (0-4) required for new passwords
    PWD_MIN_ZXCVBN_SCORE = _env_int_floor(
        "PWD_MIN_ZXCVBN_SCORE", DEFAULT_PWD_MIN_ZXCVBN_SCORE, DEFAULT_PWD_MIN_ZXCVBN_SCORE
    )
    # Number of previous passwords that can not be reused
    PWD_HISTORY_SIZE = _env_int_floor(
        "PWD_HISTORY_SIZE", DEFAULT_PWD_HISTORY_SIZE, DEFAULT_PWD_HISTORY_SIZE
    )
    # Similarity ratio (0-1) above which a new password is rejected for being
    # too close to the previous one (ceiling: 0.9, higher would allow near
    # identical passwords)
    PWD_MAX_SIMILARITY = _env_float_ceiling(
        "PWD_MAX_SIMILARITY", DEFAULT_PWD_MAX_SIMILARITY, 0.9
    )
    # If 1, users with an expired or flagged password can only access
    # the endpoints needed to change it (hard rotation enforcement)
    PWD_ROTATION_ENFORCE = int(os.getenv("PWD_ROTATION_ENFORCE", 1))

    # Account lockout: after LOGIN_MAX_ATTEMPTS consecutive failed login
    # attempts (wrong password or wrong TOTP code) the account is locked
    # until a platform administrator unlocks it. Service users are exempt
    # to avoid denial-of-service of the cornflow-airflow communication.
    # Attempts ceiling: 10.
    LOGIN_MAX_ATTEMPTS = _env_int_ceiling("LOGIN_MAX_ATTEMPTS", 5, 10)

    # Two-factor authentication (TOTP). If 1, all internal (database
    # authenticated) users except service users must enroll and provide
    # a TOTP code to log in.
    MFA_REQUIRED = int(os.getenv("MFA_REQUIRED", 1))
    # Duration in minutes of the temporary token issued to complete
    # the MFA enrollment during login (ceiling: 30)
    MFA_SETUP_TOKEN_DURATION_MINUTES = _env_int_ceiling(
        "MFA_SETUP_TOKEN_DURATION_MINUTES", 10, 30
    )

    # Per-IP rate limiting of the sensitive unauthenticated endpoints
    RATELIMIT_ENABLED = int(os.getenv("RATELIMIT_ENABLED", 1))
    # Shared storage backend for the counters. Defaults to in-memory, which
    # is per-process: production behind several gunicorn workers should set a
    # shared backend, e.g. redis://host:6379.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    # Trust the X-Forwarded-For header (only when behind a trusted reverse
    # proxy that sets it); otherwise the direct connection IP is used.
    RATELIMIT_TRUST_FORWARDED_FOR = int(
        os.getenv("RATELIMIT_TRUST_FORWARDED_FOR", 0)
    )
    RATELIMIT_LOGIN = os.getenv("RATELIMIT_LOGIN", "10 per minute")
    RATELIMIT_RECOVER = os.getenv("RATELIMIT_RECOVER", "5 per hour")
    # Return the standard rate-limit headers on responses
    RATELIMIT_HEADERS_ENABLED = True

    # Base URL of the cornflow web client, used to build the password reset
    # link sent by email (e.g. https://cornflow.example.com). When it is not
    # configured the recovery email falls back to sending a temporary
    # password.
    CORNFLOW_UI_URL = os.getenv("CORNFLOW_UI_URL")
    # Duration in minutes of the password reset link (ceiling: 60)
    PWD_RESET_TOKEN_DURATION_MINUTES = _env_int_ceiling(
        "PWD_RESET_TOKEN_DURATION_MINUTES", 30, 60
    )
    # Number of one-time backup codes generated on MFA enrollment
    MFA_BACKUP_CODES_NUMBER = _env_int_ceiling("MFA_BACKUP_CODES_NUMBER", 8, 20)

    # Structured security audit log. When 1 (default) each security-relevant
    # event (login, lockout, unlock, password/MFA/token/role changes) is
    # emitted as a JSON line on the dedicated "cornflow.audit" logger for a
    # log pipeline / SIEM to collect and retain.
    AUDIT_LOG_ENABLED = int(os.getenv("AUDIT_LOG_ENABLED", 1))

    # HTTP security response headers. They are instructions to browsers only
    # (the SPA and the docs page); cornflow-client, Airflow and the CLI ignore
    # them. Stamped on every response by a single after_request hook.
    SECURITY_HEADERS_ENABLED = int(os.getenv("SECURITY_HEADERS_ENABLED", 1))
    # HSTS forces HTTPS at the browser. Enable it only once TLS terminates in
    # front of cornflow: a browser that has seen the header will refuse plain
    # HTTP afterwards. Off by default here, on by default in production.
    HSTS_ENABLED = int(os.getenv("HSTS_ENABLED", 0))
    HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", 31536000))
    HSTS_INCLUDE_SUBDOMAINS = int(os.getenv("HSTS_INCLUDE_SUBDOMAINS", 1))
    HSTS_PRELOAD = int(os.getenv("HSTS_PRELOAD", 0))
    # Ask browsers/proxies not to cache responses (they carry auth data).
    SECURITY_NO_STORE = int(os.getenv("SECURITY_NO_STORE", 1))
    # Optional overrides of the header strings; when unset the strict defaults
    # in cornflow.shared.security are used.
    CONTENT_SECURITY_POLICY = os.getenv("CONTENT_SECURITY_POLICY")
    REFERRER_POLICY = os.getenv("REFERRER_POLICY")
    PERMISSIONS_POLICY = os.getenv("PERMISSIONS_POLICY")

    # Data isolation between internal (platform) and client users: when 1
    # (default) the instances, executions and cases created by a user holding
    # a platform role are invisible to client users — including client admins,
    # who otherwise see every object of the deployment. Keeps operator test
    # data out of sight on shared or staging environments.
    PLATFORM_DATA_ISOLATION = int(os.getenv("PLATFORM_DATA_ISOLATION", 1))

    # Interactive API docs (Swagger UI at /swagger-ui/). Enabled by default,
    # but disabled in production (see the Production config) to shrink the
    # attack surface and keep the deny-by-default CSP.
    DOCS_ENABLED = int(os.getenv("CORNFLOW_DOCS_ENABLED", 1))


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
    SIGNUP_ACTIVATED = SIGNUP_WITH_NO_AUTH
    # MFA is disabled for the generic test suite. Specific MFA tests
    # activate it explicitly.
    MFA_REQUIRED = 0
    # Rate limiting is disabled for the generic test suite (which makes many
    # rapid login calls). Specific rate-limit tests enable it explicitly.
    RATELIMIT_ENABLED = 0
    # Low bcrypt work factor to keep the test suite fast (production uses 12)
    BCRYPT_LOG_ROUNDS = 4


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
    # Cross-origin requests are default-closed: only the origins explicitly
    # listed in CORS_ORIGINS (e.g. the cornflow-ui URL) are allowed.
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
    # The interactive docs are off by default in production. Re-enable with
    # CORNFLOW_DOCS_ENABLED=1 (this relaxes the need for a strict CSP).
    DOCS_ENABLED = int(os.getenv("CORNFLOW_DOCS_ENABLED", 0))
    # HSTS on by default: a production ENS deployment terminates TLS in front.
    # Disable with HSTS_ENABLED=0 if TLS is not yet in place.
    HSTS_ENABLED = int(os.getenv("HSTS_ENABLED", 1))


app_config = {
    "development": Development,
    "testing": Testing,
    "production": Production,
    "testing-oauth": TestingOpenAuth,
    "testing-root": TestingApplicationRoot,
    "testing-databricks": TestingDatabricks,
    "testing-ratelimit": TestingRateLimit,
}
