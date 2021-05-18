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
