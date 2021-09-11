"""
Constants values used in schemas functions.
"""

STRING_TYPE = "String"
BOOLEAN_TYPE = "Boolean"
INTEGER_TYPE = "Integer"
FLOAT_TYPE = "Float"
BASIC_TYPES = [STRING_TYPE, BOOLEAN_TYPE, INTEGER_TYPE, FLOAT_TYPE]

JSON_TYPES = {
    "string": STRING_TYPE,
    "number": FLOAT_TYPE,
    "integer": INTEGER_TYPE,
    "null": None,
    "boolean": BOOLEAN_TYPE,
}

DATASCHEMA = "DataSchema"

INSTANCE_SCHEMA = "instance"
SOLUTION_SCHEMA = "solution"
CONFIG_SCHEMA = "config"

# why it stopped
STATUS_NOT_SOLVED = 0
STATUS_OPTIMAL = 1
STATUS_INFEASIBLE = -1
STATUS_UNBOUNDED = -2
STATUS_UNDEFINED = -3
STATUS_TIME_LIMIT = 2
STATUS_MEMORY_LIMIT = 3
STATUS_NODE_LIMIT = 4

# is there a solution?
SOLUTION_STATUS_INFEASIBLE = 0
SOLUTION_STATUS_FEASIBLE = 2


class InvalidUsage(Exception):
    status_code = 400
    error = "Unknown error"

    def __init__(self, error=None, status_code=None, payload=None):
        Exception.__init__(self)
        if error is not None:
            self.error = error
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["error"] = self.error
        return rv


class AirflowError(InvalidUsage):
    status_code = 400

    def __init__(self, error, status_code=None, payload=None):
        self.error = error
        self.payload = payload
        if status_code is not None:
            self.status_code = status_code
