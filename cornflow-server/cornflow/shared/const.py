"""
In this file we import the values for different constants on cornflow server
"""

# CORNFLOW BACKEND
AIRFLOW_BACKEND = 1
DATABRICKS_BACKEND = 2


CORNFLOW_VERSION = "1.3.7rc1"
INTERNAL_TOKEN_ISSUER = "cornflow"

# Purpose claims used on temporary restricted tokens. Tokens carrying a
# purpose claim are only accepted by the endpoints mapped below:
# - mfa_setup: issued during login when a user still has to enroll in
#   two-factor authentication
# - pwd_reset: carried inside the password reset link sent by email
TOKEN_PURPOSE_MFA_SETUP = "mfa_setup"
TOKEN_PURPOSE_PWD_RESET = "pwd_reset"

# Endpoint names (as registered on the api) each purpose token can access
TOKEN_PURPOSE_ALLOWED_ENDPOINTS = {
    TOKEN_PURPOSE_MFA_SETUP: ["mfa-setup", "mfa-verify"],
    TOKEN_PURPOSE_PWD_RESET: ["reset-password"],
}

# Endpoints (name -> allowed methods) that stay reachable when the user's
# password has expired and password rotation is enforced: the user can check
# their token, review their own profile (and roles, needed by the web client
# to render the settings screen) and change their password.
PWD_ROTATION_ALLOWED_ENDPOINTS = {
    "user-detail": ["GET", "PUT"],
    "token": ["GET"],
    "user-roles": ["GET"],
    "login": ["POST"],
    "signup": ["POST"],
}

# endpoints responses for health check
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"

# execution states for executions table
EXEC_STATE_CORRECT = 1
EXEC_STATE_MANUAL = 2
EXEC_STATE_RUNNING = 0
EXEC_STATE_ERROR = -1
EXEC_STATE_STOPPED = -2
EXEC_STATE_ERROR_START = -3
EXEC_STATE_NOT_RUN = -4
EXEC_STATE_UNKNOWN = -5
EXEC_STATE_SAVING = -6
EXEC_STATE_QUEUED = -7

EXECUTION_STATE_MESSAGE_DICT = {
    EXEC_STATE_CORRECT: "The execution has been solved correctly.",
    EXEC_STATE_RUNNING: "The execution is currently running.",
    EXEC_STATE_ERROR: "The execution has found an error.",
    EXEC_STATE_STOPPED: "The execution has stopped running.",
    EXEC_STATE_ERROR_START: "The execution couldn't start running.",
    EXEC_STATE_NOT_RUN: "The execution wasn't run by user choice.",
    EXEC_STATE_UNKNOWN: "The execution has an unknown error.",
    EXEC_STATE_SAVING: "The execution executed ok but failed while saving it.",
    EXEC_STATE_MANUAL: "The execution was loaded manually.",
    EXEC_STATE_QUEUED: "The execution is currently queued.",
}

# derived constants
MIN_EXECUTION_STATUS_CODE = min(EXECUTION_STATE_MESSAGE_DICT.keys())
MAX_EXECUTION_STATUS_CODE = max(EXECUTION_STATE_MESSAGE_DICT.keys())
DEFAULT_EXECUTION_CODE = EXEC_STATE_RUNNING

AIRFLOW_TO_STATE_MAP = dict(
    success=EXEC_STATE_CORRECT,
    running=EXEC_STATE_RUNNING,
    failed=EXEC_STATE_ERROR,
    queued=EXEC_STATE_QUEUED,
)
# SIGNUP OPTIONS
# NO_SIGNUP: no signup endpoint
# SIGNUP_WITH_NO_AUTH: signup endpoint with no auth
# SIGNUP_WITH_AUTH: signup endpoint with auth
NO_SIGNUP = 0
SIGNUP_WITH_NO_AUTH = 1
SIGNUP_WITH_AUTH = 2

DATABRICKS_TO_STATE_MAP = dict(
    BLOCKED=EXEC_STATE_QUEUED,
    PENDING=EXEC_STATE_QUEUED,
    QUEUED=EXEC_STATE_QUEUED,
    RUNNING=EXEC_STATE_RUNNING,
    TERMINATING=EXEC_STATE_RUNNING,
    SUCCESS=EXEC_STATE_CORRECT,
    USER_CANCELED=EXEC_STATE_STOPPED,
    OTHER_FINISH_ERROR=EXEC_STATE_ERROR,
    RUN_EXECUTION_ERROR=EXEC_STATE_ERROR,
)

DATABRICKS_FINISH_TO_STATE_MAP = dict(
    SUCCESS=EXEC_STATE_CORRECT,
    USER_CANCELED=EXEC_STATE_STOPPED,
)

DATABRICKS_TERMINATE_STATE = "TERMINATED"
# These codes and names are inherited from flask app builder in order to have the same names and values
# as this library that is the base of airflow
AUTH_DB = 1
AUTH_LDAP = 2
AUTH_OAUTH = 4
AUTH_OID = 0

# USER_ACCESS_ALL_OBJECTS values
USER_ACCESS_ALL_OBJECTS_NO = 0
USER_ACCESS_ALL_OBJECTS_YES = 1

# OID possible providers
OID_PROVIDER_AZURE = 1
OID_OTHER = 2

GET_ACTION = 1
PATCH_ACTION = 2
POST_ACTION = 3
PUT_ACTION = 4
DELETE_ACTION = 5

ALL_DEFAULT_ACTIONS = [GET_ACTION, PATCH_ACTION, POST_ACTION, PUT_ACTION, DELETE_ACTION]

DUMMY_ROLE = 0
VIEWER_ROLE = 1
PLANNER_ROLE = 2
# The admin role is meant for client administrators (they manage the users
# and data of their own deployment)
ADMIN_ROLE = 3
# The service role is reserved for machine-to-machine service accounts
SERVICE_ROLE = 4
# Platform administrators operate the platform itself: they are the only
# ones that can unlock accounts locked after too many failed login attempts
PLATFORM_ADMIN_ROLE = 5

ALL_DEFAULT_ROLES = [
    VIEWER_ROLE,
    PLANNER_ROLE,
    ADMIN_ROLE,
    SERVICE_ROLE,
    PLATFORM_ADMIN_ROLE,
]

ACTIONS_MAP = {
    GET_ACTION: "can_get",
    PATCH_ACTION: "can_patch",
    POST_ACTION: "can_post",
    PUT_ACTION: "can_put",
    DELETE_ACTION: "can_delete",
}

PERMISSION_METHOD_MAP = {
    "GET": GET_ACTION,
    "PATCH": PATCH_ACTION,
    "POST": POST_ACTION,
    "PUT": PUT_ACTION,
    "DELETE": DELETE_ACTION,
}

ROLES_MAP = {
    DUMMY_ROLE: "dummy",
    PLANNER_ROLE: "planner",
    VIEWER_ROLE: "viewer",
    ADMIN_ROLE: "admin",
    SERVICE_ROLE: "service",
    PLATFORM_ADMIN_ROLE: "platform_admin",
}

BASE_PERMISSION_ASSIGNATION = [
    (VIEWER_ROLE, GET_ACTION),
    (PLANNER_ROLE, GET_ACTION),
    (PLANNER_ROLE, PATCH_ACTION),
    (PLANNER_ROLE, POST_ACTION),
    (PLANNER_ROLE, PUT_ACTION),
    (PLANNER_ROLE, DELETE_ACTION),
    (ADMIN_ROLE, GET_ACTION),
    (ADMIN_ROLE, PATCH_ACTION),
    (ADMIN_ROLE, POST_ACTION),
    (ADMIN_ROLE, PUT_ACTION),
    (ADMIN_ROLE, DELETE_ACTION),
    (SERVICE_ROLE, GET_ACTION),
    (SERVICE_ROLE, PATCH_ACTION),
    (SERVICE_ROLE, PUT_ACTION),
    (SERVICE_ROLE, DELETE_ACTION),
    (SERVICE_ROLE, POST_ACTION),
    (PLATFORM_ADMIN_ROLE, GET_ACTION),
    (PLATFORM_ADMIN_ROLE, PATCH_ACTION),
    (PLATFORM_ADMIN_ROLE, POST_ACTION),
    (PLATFORM_ADMIN_ROLE, PUT_ACTION),
    (PLATFORM_ADMIN_ROLE, DELETE_ACTION),
]

EXTRA_PERMISSION_ASSIGNATION = [
    (DUMMY_ROLE, GET_ACTION, "user-detail"),
    (DUMMY_ROLE, PUT_ACTION, "user-detail"),
    (VIEWER_ROLE, PUT_ACTION, "user-detail"),
    (DUMMY_ROLE, GET_ACTION, "user-roles"),
    (VIEWER_ROLE, GET_ACTION, "user-roles"),
    (PLANNER_ROLE, GET_ACTION, "user-roles"),
    (SERVICE_ROLE, GET_ACTION, "user-roles"),
    (VIEWER_ROLE, GET_ACTION, "execution-files"),
    (PLANNER_ROLE, GET_ACTION, "execution-files"),
    (ADMIN_ROLE, GET_ACTION, "execution-files"),
    (VIEWER_ROLE, POST_ACTION, "mfa-setup"),
    (VIEWER_ROLE, POST_ACTION, "mfa-verify"),
    (VIEWER_ROLE, DELETE_ACTION, "user-mfa"),
    (VIEWER_ROLE, PUT_ACTION, "reset-password"),
    (DUMMY_ROLE, PUT_ACTION, "reset-password"),
]

# are there execution files?
EXECUTION_FILES_STATUS_NOT_GENERATED = 0
EXECUTION_FILES_STATUS_ERROR = -1
EXECUTION_FILES_STATUS_DELETED = -2
EXECUTION_FILES_STATUS_NOT_UP_TO_DATE = -3
EXECUTION_FILES_STATUS_OK = 1

EXECUTION_FILES_STATUS_MESSAGE_DICT = {
    EXECUTION_FILES_STATUS_NOT_GENERATED: "The output files were not generated for this execution",
    EXECUTION_FILES_STATUS_ERROR: "The generation of the execution files failed. Please contact support.",
    EXECUTION_FILES_STATUS_DELETED: "The requested files have been deleted. Please wait while they are generated again.",
    EXECUTION_FILES_STATUS_NOT_UP_TO_DATE: "The requested files are not up-to-date. Please wait while they are generated again.",
    EXECUTION_FILES_STATUS_OK: "The files were generated successfully.",
}

# Costants for messages that are given back on exceptions
AIRFLOW_NOT_REACHABLE_MSG = "Airflow is not reachable"
DAG_PAUSED_MSG = "The dag exists but it is paused in airflow"
AIRFLOW_ERROR_MSG = "Airflow responded with an error:"
DATA_DOES_NOT_EXIST_MSG = "The data entity does not exist on the database"

# Conditional endpoints
CONDITIONAL_ENDPOINTS = {
    "signup": "/signup/",
    "login": "/login/",
}


# Orchestrator constants
config_orchestrator = {
    "airflow": {
        "name": "Airflow",
        "def_schema": "solve_model_dag",
        "run_id": "dag_run_id",
    },
    "databricks": {
        "name": "Databricks",
        "def_schema": "979073949072767",
        "run_id": "run_id",
    },
}
