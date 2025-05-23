"""
In this file we import the values for different constants on cornflow server
"""
CORNFLOW_VERSION = "1.2.2"
INTERNAL_TOKEN_ISSUER = "cornflow"

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

# These codes and names are inherited from flask app builder in order to have the same names and values
# as this library that is the base of airflow
AUTH_DB = 1
AUTH_LDAP = 2
AUTH_OAUTH = 4
AUTH_OID = 0

GET_ACTION = 1
PATCH_ACTION = 2
POST_ACTION = 3
PUT_ACTION = 4
DELETE_ACTION = 5

ALL_DEFAULT_ACTIONS = [GET_ACTION, PATCH_ACTION, POST_ACTION, PUT_ACTION, DELETE_ACTION]

VIEWER_ROLE = 1
PLANNER_ROLE = 2
ADMIN_ROLE = 3
SERVICE_ROLE = 4

ALL_DEFAULT_ROLES = [VIEWER_ROLE, PLANNER_ROLE, ADMIN_ROLE, SERVICE_ROLE]

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
    PLANNER_ROLE: "planner",
    VIEWER_ROLE: "viewer",
    ADMIN_ROLE: "admin",
    SERVICE_ROLE: "service",
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
]

EXTRA_PERMISSION_ASSIGNATION = [
    (VIEWER_ROLE, PUT_ACTION, "user-detail"),
]

# migrations constants
MIGRATIONS_DEFAULT_PATH = "./cornflow/migrations"

# Costants for messages that are given back on exceptions
AIRFLOW_NOT_REACHABLE_MSG = "Airflow is not reachable"
DAG_PAUSED_MSG = "The dag exists but it is paused in airflow"
AIRFLOW_ERROR_MSG = "Airflow responded with an error:"
DATA_DOES_NOT_EXIST_MSG = "The data entity does not exist on the database"
