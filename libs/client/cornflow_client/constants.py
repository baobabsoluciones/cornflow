"""
Constants values used in schemas functions.
"""
import pulp as pl
from ortools.sat.python import cp_model


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
STATUS_FEASIBLE = 2
STATUS_MEMORY_LIMIT = 3
STATUS_NODE_LIMIT = 4
STATUS_TIME_LIMIT = 5
STATUS_LICENSING_PROBLEM = -5
STATUS_QUEUED = -7

# is there a solution?
SOLUTION_STATUS_INFEASIBLE = 0
SOLUTION_STATUS_FEASIBLE = 2

PYOMO_STOP_MAPPING = {
    "unbounded": STATUS_UNBOUNDED,
    "infeasible": STATUS_INFEASIBLE,
    "invalidProblem": STATUS_NOT_SOLVED,
    "solverFailure": STATUS_NOT_SOLVED,
    "internalSolverError": STATUS_NOT_SOLVED,
    "error": STATUS_NOT_SOLVED,
    "userInterrupt": STATUS_NOT_SOLVED,
    "resourceInterrupt": STATUS_NOT_SOLVED,
    "licensingProblem": STATUS_LICENSING_PROBLEM,
    "maxTimeLimit": STATUS_TIME_LIMIT,
    "maxIterations": STATUS_TIME_LIMIT,
    "maxEvaluations": STATUS_TIME_LIMIT,
    "globallyOptimal": STATUS_OPTIMAL,
    "locallyOptimal": STATUS_OPTIMAL,
    "optimal": STATUS_OPTIMAL,
    "minFunctionValue": STATUS_UNDEFINED,
    "minStepLength": STATUS_UNDEFINED,
    "other": STATUS_UNDEFINED,
    "intermediateNonInteger": STATUS_TIME_LIMIT,
    "feasible": STATUS_TIME_LIMIT,
    "noSolution": STATUS_TIME_LIMIT,
}

PYOMO_STATUS_MAPPING = {
    "ok": SOLUTION_STATUS_FEASIBLE,
    "warning": SOLUTION_STATUS_INFEASIBLE,
    "error": SOLUTION_STATUS_INFEASIBLE,
    "aborted": SOLUTION_STATUS_INFEASIBLE,
    "unknown": SOLUTION_STATUS_INFEASIBLE,
}

ORTOOLS_STATUS_MAPPING = {
    cp_model.OPTIMAL: STATUS_OPTIMAL,
    cp_model.FEASIBLE: STATUS_FEASIBLE,
    cp_model.INFEASIBLE: STATUS_INFEASIBLE,
    cp_model.UNKNOWN: STATUS_UNDEFINED,
    cp_model.MODEL_INVALID: STATUS_UNDEFINED,
}

PULP_STATUS_MAPPING = {
    pl.LpStatusInfeasible: STATUS_INFEASIBLE,
    pl.LpStatusNotSolved: STATUS_NOT_SOLVED,
    pl.LpStatusOptimal: STATUS_OPTIMAL,
    pl.LpStatusUnbounded: STATUS_UNBOUNDED,
    pl.LpStatusUndefined: STATUS_UNDEFINED,
}


class AirflowError(Exception):
    status_code = 400

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


class NoSolverException(Exception):
    pass


class BadConfiguration(Exception):
    pass


class BadInstance(Exception):
    pass


class BadSolution(Exception):
    pass
