EXEC_STATE_CORRECT = 1
EXEC_STATE_RUNNING = 0
EXEC_STATE_ERROR = -1
EXEC_STATE_STOPPED = -2
EXEC_STATE_ERROR_START = -3
EXEC_STATE_NOT_RUN = -4
EXEC_STATE_UNKNOWN = -5

EXECUTION_STATE_MESSAGE_DICT = {EXEC_STATE_CORRECT: "The execution has been solved correctly.",
                                EXEC_STATE_RUNNING: "The execution is currently running.",
                                EXEC_STATE_ERROR: "The execution has found an error.",
                                EXEC_STATE_STOPPED: "The execution has stopped running.",
                                EXEC_STATE_ERROR_START: "The execution couldn't start running.",
                                EXEC_STATE_NOT_RUN: "The execution wasn't run by user choice.",
                                EXEC_STATE_UNKNOWN: "The execution has an unknown error."}

# derived constants
MIN_EXECUTION_STATUS_CODE = min(EXECUTION_STATE_MESSAGE_DICT.keys())
MAX_EXECUTION_STATUS_CODE = max(EXECUTION_STATE_MESSAGE_DICT.keys())
DEFAULT_EXECUTION_CODE = EXEC_STATE_RUNNING

AIRFLOW_TO_STATE_MAP = dict(success=EXEC_STATE_CORRECT,
                            running=EXEC_STATE_RUNNING,
                            failed=EXEC_STATE_ERROR
                            )