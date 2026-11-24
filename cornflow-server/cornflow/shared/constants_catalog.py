"""
Catalog of the codes that clients find in the responses of the API
(execution state, solution status, solver status, ...) with their name and
message.

Everything is built from the constants of ``cornflow.shared.const`` and
``cornflow_client.constants``, so there is a single source of truth: a new
constant that is not in its message dictionary makes the build fail.
"""

from cornflow_client import constants as client_constants

from cornflow.shared import const as server_const


def _named_codes(module, prefix):
    """
    Returns {code: name} for the integer constants of ``module`` that start with ``prefix``.
    The name is the rest of the constant name in lower case.
    """
    return {
        value: name[len(prefix):].lower()
        for name, value in vars(module).items()
        if name.startswith(prefix)
        and isinstance(value, int)
        and not isinstance(value, bool)
    }


# key in the response -> (module, prefix of the constants, dict with the messages)
_ENUMS = {
    # "state" of an execution
    "execution_states": (
        server_const,
        "EXEC_STATE_",
        server_const.EXECUTION_STATE_MESSAGE_DICT,
    ),
    # "sol_code" of the execution log
    "solution_status": (
        client_constants,
        "SOLUTION_STATUS_",
        server_const.SOLUTION_STATUS_MESSAGE_DICT,
    ),
    # "status_code" of the execution log
    "solver_status": (
        client_constants,
        "STATUS_",
        client_constants.STATUS_CONV,
    ),
    # "data_state" / files status of an execution
    "execution_files_status": (
        server_const,
        "EXECUTION_FILES_STATUS_",
        server_const.EXECUTION_FILES_STATUS_MESSAGE_DICT,
    ),
}


def get_constants_catalog():
    """
    :return: a dict with, for each enum, a list of {code, name, message} sorted by code
    """
    catalog = {}
    for key, (module, prefix, messages) in _ENUMS.items():
        names = _named_codes(module, prefix)
        catalog[key] = [
            dict(code=code, name=names[code], message=messages[code])
            for code in sorted(names)
        ]
    return catalog
