PREFIX = ""
INSTANCE_PATH = "./cornflow/tests/data/new_instance.json"
INSTANCES_LIST = [INSTANCE_PATH, "./cornflow/tests/data/new_instance_2.json"]
INSTANCE_URL = PREFIX + "/instance/"

EXECUTION_PATH = "./cornflow/tests/data/new_execution.json"
EXECUTIONS_LIST = [EXECUTION_PATH, "./cornflow/tests/data/new_execution_2.json"]
EXECUTION_URL = PREFIX + "/execution/"
EXECUTION_URL_NORUN = EXECUTION_URL + "?run=0"

CASE_PATH = "./cornflow/tests/data/new_case_raw.json"
CASES_LIST = [CASE_PATH, "./cornflow/tests/data/new_case_raw_2.json"]
CASE_LIST_URL = PREFIX + "/case/"
CASE_INSTANCE_URL = PREFIX + "/case/instance/"
CASE_RAW_URL = PREFIX + "/case/raw/"
CASE_COPY_URL = PREFIX + "/case/copy/"
CASE_TO_INSTANCE_URL = PREFIX + "/case/live/"

LOGIN_URL = PREFIX + "/login/"
SIGNUP_URL = PREFIX + "/signup/"
USER_URL = PREFIX + "/user/"

SCHEMA_URL = PREFIX + "/schema/"


INSTANCE_FILE_URL = PREFIX + "/instancefile/"

HEALTH_URL = PREFIX + "/health/"
