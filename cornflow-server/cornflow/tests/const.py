import os

path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


PREFIX = ""
INSTANCE_PATH = _get_file("./data/new_instance.json")
EMPTY_INSTANCE_PATH = _get_file("./data/empty_instance.json")
INSTANCES_LIST = [INSTANCE_PATH, _get_file("./data/new_instance_2.json")]
INSTANCE_URL = PREFIX + "/instance/"
INSTANCE_MPS = _get_file("./data/test_mps.mps")
INSTANCE_GC_20 = _get_file("./data/gc_20_7.json")
INSTANCE_FILE_FAIL = _get_file("./unit/test_instances.py")

EXECUTION_PATH = _get_file("./data/new_execution.json")
CUSTOM_CONFIG_PATH = _get_file("./data/new_execution_custom_config.json")
BAD_EXECUTION_PATH = _get_file("./data/bad_execution.json")
EXECUTION_SOLUTION_PATH = _get_file("./data/new_execution_solution.json")
EXECUTIONS_LIST = [EXECUTION_PATH, _get_file("./data/new_execution_2.json")]
EXECUTION_URL = PREFIX + "/execution/"
EXECUTION_URL_NORUN = EXECUTION_URL + "?run=0"
DAG_URL = PREFIX + "/dag/"
DATA_CHECK_EXECUTION_URL = PREFIX + "/data-check/execution/"
DATA_CHECK_INSTANCE_URL = PREFIX + "/data-check/instance/"
DATA_CHECK_CASE_URL = PREFIX + "/data-check/case/"

CASE_PATH = _get_file("./data/new_case_raw.json")
CASES_LIST = [CASE_PATH, _get_file("./data/new_case_raw_2.json")]
CASE_URL = PREFIX + "/case/"
CASE_INSTANCE_URL = PREFIX + "/case/instance/"

FULL_CASE_PATH = _get_file("./data/full_case_raw.json")
FULL_CASE_LIST = [FULL_CASE_PATH, _get_file("./data/full_case_raw_2.json")]

JSON_PATCH_GOOD_PATH = _get_file("./data/json_patch_good.json")
JSON_PATCH_BAD_PATH = _get_file("./data/json_patch_bad.json")
FULL_CASE_JSON_PATCH_1 = _get_file("./data/full_case_patch.json")

LOGIN_URL = PREFIX + "/login/"
SIGNUP_URL = PREFIX + "/signup/"
TOKEN_URL = PREFIX + "/token/"
USER_URL = PREFIX + "/user/"
RECOVER_PASSWORD_URL = PREFIX + "/user/recover-password/"

SCHEMA_URL = PREFIX + "/schema/"
EXAMPLE_URL = PREFIX + "/example/"

INSTANCE_FILE_URL = PREFIX + "/instancefile/"

HEALTH_URL = PREFIX + "/health/"

ACTIONS_URL = PREFIX + "/action/"
PERMISSION_URL = PREFIX + "/permission/"

ROLES_URL = PREFIX + "/roles/"
USER_ROLE_URL = PREFIX + "/user/role/"

APIVIEW_URL = PREFIX + "/apiview/"

DEPLOYED_DAG_URL = PREFIX + "/dag/deployed/"

TABLES_URL = PREFIX + "/table/"
ALARMS_URL = PREFIX + "/alarms/"
MAIN_ALARMS_URL = PREFIX + "/main-alarms/"

LICENSES_URL = PREFIX + "/licences/"

PUBLIC_DAGS = [
    "solve_model_dag",
    "gc",
    "timer",
    "bar_cutting",
    "facility_location",
    "graph_coloring",
    "hk_2020_dag",
    "knapsack",
    "roadef",
    "rostering",
    "tsp",
    "vrp",
]
