PREFIX = ""
INSTANCE_PATH = "./cornflow/tests/data/new_instance.json"
INSTANCES_LIST = [INSTANCE_PATH, "./cornflow/tests/data/new_instance_2.json"]
INSTANCE_URL = PREFIX + "/instance/"

EXECUTION_PATH = "./cornflow/tests/data/new_execution.json"
EXECUTIONS_LIST = [EXECUTION_PATH, "./cornflow/tests/data/new_execution_2.json"]
EXECUTION_URL = PREFIX + "/execution/"
EXECUTION_URL_NORUN = EXECUTION_URL + "?run=0"
DAG_URL = PREFIX + "/dag/"

CASE_PATH = "./cornflow/tests/data/new_case_raw.json"
CASES_LIST = [CASE_PATH, "./cornflow/tests/data/new_case_raw_2.json"]
CASE_URL = PREFIX + "/case/"
CASE_INSTANCE_URL = PREFIX + "/case/instance/"

FULL_CASE_PATH = "./cornflow/tests/data/full_case_raw.json"
FULL_CASE_LIST = [FULL_CASE_PATH, "./cornflow/tests/data/full_case_raw_2.json"]

JSON_PATCH_GOOD_PATH = "./cornflow/tests/data/json_patch_good.json"
JSON_PATCH_BAD_PATH = "./cornflow/tests/data/json_patch_bad.json"
FULL_CASE_JSON_PATCH_1 = "./cornflow/tests/data/full_case_patch.json"

LOGIN_URL = PREFIX + "/login/"
SIGNUP_URL = PREFIX + "/signup/"
USER_URL = PREFIX + "/user/"

SCHEMA_URL = PREFIX + "/schema/"


INSTANCE_FILE_URL = PREFIX + "/instancefile/"

HEALTH_URL = PREFIX + "/health/"

ACTIONS_URL = PREFIX + "/action/"
PERMISSION_URL = PREFIX + "/permission/"

ROLES_URL = PREFIX + "/roles/"
USER_ROLE_URL = PREFIX + "/user/role/"

APIVIEW_URL = PREFIX + "/apiview/"
