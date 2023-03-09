"""
Functions to format the error messages to be sent by the api.
"""
import traceback as tb
from cornflow_client.constants import AirflowError
from cornflow_core.exceptions import InvalidUsage

from cornflow.shared.const import EXEC_STATE_ERROR_START


def format_error(
    error,
    error_type=InvalidUsage,
    message="Unexpected error",
    state=EXEC_STATE_ERROR_START,
):
    """
    Format the error in order to return a proper error message to airflow.
    known error are directly returned and other exceptions are formatted.

    :param error: A python error (Exception class)
    :return: raise the error with proper message and payload.
    """
    known_errors = (AirflowError, InvalidUsage)
    if isinstance(error, known_errors):
        raise error
    else:
        stack_trace = get_trace_back(error)
        raise error_type(
            error=str(error),
            payload={
                "message": message,
                "trace_back": stack_trace,
                "error arguments": {i: e for i, e in enumerate(error.args)},
                "state": state,
            },
        )


def get_trace_back(error):
    """
    Get the traceback of an error as a list of strings.

    :param error: a python error (Exception)
    :return: a list of strings
    """
    trace_back = tb.extract_tb(error.__traceback__)
    return [
        f"File: {f} , line {ln}, function: {fun}, message: {msg}"
        for f, ln, fun, msg in trace_back
    ]