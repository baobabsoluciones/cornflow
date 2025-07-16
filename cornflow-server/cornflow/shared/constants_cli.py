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
INSTANCE_CHECKS_SCHEMA = "instance_checks"
SOLUTION_CHECKS_SCHEMA = "solution_checks"

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

# Associated string
STATUS_CONV = {
    STATUS_OPTIMAL: "Optimal",
    STATUS_TIME_LIMIT: "Time limit",
    STATUS_INFEASIBLE: "Infeasible",
    STATUS_UNDEFINED: "Unknown",
    STATUS_NOT_SOLVED: "Not solved",
    STATUS_UNBOUNDED: "Unbounded",
    STATUS_FEASIBLE: "Feasible",
    STATUS_MEMORY_LIMIT: "Memory limit",
    STATUS_NODE_LIMIT: "Node limit",
    STATUS_LICENSING_PROBLEM: "Licensing problem",
    STATUS_QUEUED: "Queued",
}

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

PARAMETER_SOLVER_TRANSLATING_MAPPING = {
    ("abs_gap", "pyomo", "cbc"): "allow",
    ("rel_gap", "pyomo", "cbc"): "ratio",
    ("cutoff", "pyomo", "cbc"): "cuts",
    ("bar_iter_limit", "pyomo", "cbc"): "barr",
    ("best_obj_stop", "pyomo", "cbc"): "primalT",
    ("iteration_limit", "pyomo", "cbc"): "maxIt",
    ("solution_limit", "pyomo", "cbc"): "maxSaved",
    ("time_limit", "pyomo", "cbc"): "sec",
    ("timeLimit", "pyomo", "cbc"): "sec",
    ("pump_passes", "pyomo", "cbc"): "pumpC",
    ("heuristics", "pyomo", "cbc"): "heur",
    ("is_mip", "pulp", "cbc"): "mip",
    ("abs_gap", "pulp", "cbc"): "gapAbs",
    ("rel_gap", "pulp", "cbc"): "gapRel",
    ("cutoff", "pulp", "cbc"): "cuts",
    ("time_limit", "pulp", "cbc"): "timeLimit",
    ("timeLimit", "pulp", "cbc"): "timeLimit",
    ("threads", "pulp", "cbc"): "threads",
    ("presolve", "pulp", "cbc"): "presolve",
    ("msg", "pulp", "cbc"): "msg",
    ("abs_gap", "pyomo", "gurobi"): "MIPGapAbs",
    ("rel_gap", "pyomo", "gurobi"): "MIPGap",
    ("time_limit", "pyomo", "gurobi"): "TimeLimit",
    ("timeLimit", "pyomo", "gurobi"): "TimeLimit",
    ("presolve", "pyomo", "gurobi"): "Presolve",
    ("iteration_limit", "pyomo", "gurobi"): "IterationLimit",
    ("bar_iter_limit", "pyomo", "gurobi"): "BarIterLimit",
    ("best_obj_stop", "pyomo", "gurobi"): "BestObjStop",
    ("cutoff", "pyomo", "gurobi"): "Cutoff",
    ("mem_limit", "pyomo", "gurobi"): "MemLimit",
    ("solution_limit", "pyomo", "gurobi"): "SolutionLimit",
    ("branch_dir", "pyomo", "gurobi"): "BranchDir",
    ("pump_passes", "pyomo", "gurobi"): "PumpPasses",
    ("heuristics", "pyomo", "gurobi"): "Heuristics",
    ("threads", "pyomo", "gurobi"): "threads",
    ("msg", "pyomo", "gurobi"): "OutputFlag",
    ("is_mip", "pulp", "gurobi"): "mip",
    ("abs_gap", "pulp", "gurobi"): "gapAbs",
    ("rel_gap", "pulp", "gurobi"): "gapRel",
    ("time_limit", "pulp", "gurobi"): "timeLimit",
    ("timeLimit", "pulp", "gurobi"): "timeLimit",
    ("presolve", "pulp", "gurobi"): "presolve",
    ("feasibility_tol", "pulp", "gurobi"): "FeasibilityTol",
    ("iteration_limit", "pulp", "gurobi"): "IterationLimit",
    ("msg", "pulp", "gurobi"): "OutputFlag",
    ("abs_gap", "pyomo", "scip"): "limits/absgap",
    ("rel_gap", "pyomo", "scip"): "limits/gap",
    ("time_limit", "pyomo", "scip"): "limits/time",
    ("timeLimit", "pyomo", "scip"): "limits/time",
    ("threads", "pyomo", "scip"): "threads",
    ("bar_tol", "pyomo", "scip"): "numerics/barrierconvtol",
    ("cutoff_breaker", "pyomo", "scip"): "heuristics/shiftandpropagate/cutoffbreaker",
    ("iteration_limit", "pyomo", "scip"): "lp/iterlim",
    ("mem_limit", "pyomo", "scip"): "limits/memory",
    ("solution_limit", "pyomo", "scip"): "limits/maxsol",
    ("pump_passes", "pyomo", "scip"): "heuristics/feaspump/maxdepth",
    ("presolve", "pyomo", "scip"): "presolve",
    ("nlp_tol", "pyomo", "scip"): "heuristics/subnlp/opttol",
    ("cutoff", "pyomo", "scip"): "heuristics/subnlp/setcutoff",
    ("nlp_iteration_limit", "pyomo", "scip"): "heuristics/subnlp/itermin",
    ("is_mip", "pulp", "scip"): "mip",
    ("abs_gap", "pulp", "scip"): "gapAbs",
    ("rel_gap", "pulp", "scip"): "gapRel",
    ("time_limit", "pulp", "scip"): "timeLimit",
    ("timeLimit", "pulp", "scip"): "timeLimit",
    ("threads", "pulp", "scip"): "threads",
    ("max_nodes", "pulp", "scip"): "maxNodes",
    ("iteration_limit", "pulp", "scip"): "lp/iterlim",
    ("mem_limit", "pulp", "scip"): "limits/memory",
    ("cutoff_breaker", "pulp", "scip"): "heuristics/shiftandpropagate/cutoffbreaker",
    ("presolve", "pulp", "scip"): "presolve",
    ("solution_limit", "pulp", "scip"): "limits/maxsol",
    ("nlp_iteration_limit", "pulp", "scip"): "heuristics/subnlp/itermin",
    ("msg", "pulp", "scip"): "msg",
    ("rel_gap", "pyomo", "highs"): "mip_rel_gap",
    ("abs_gap", "pyomo", "highs"): "mip_abs_gap",
    ("time_limit", "pyomo", "highs"): "time_limit",
    ("timeLimit", "pyomo", "highs"): "time_limit",
    ("presolve", "pyomo", "highs"): "presolve",
    ("parallel", "pyomo", "highs"): "parallel",
    ("crossover", "pyomo", "highs"): "run_crossover",
    ("heuristics", "pyomo", "highs"): "mip_heuristic_effort",
    ("is_mip", "pulp", "highs"): "mip",
    ("abs_gap", "pulp", "highs"): "gapAbs",
    ("rel_gap", "pulp", "highs"): "gapRel",
    ("time_limit", "pulp", "highs"): "timeLimit",
    ("timeLimit", "pulp", "highs"): "timeLimit",
    ("presolve", "pulp", "highs"): "presolve",
    ("threads", "pulp", "highs"): "threads",
    ("heuristics", "pulp", "highs"): "mip_heuristic_effort",
    ("msg", "pulp", "highs"): "msg",
}

SOLVER_CONVERTER = {
    # PYOMO
    "gurobi": "gurobi",
    "cbc": "cbc",
    "scip": "scip",
    "highs": "highs",
    "appsi_highs": "highs",
    # PULP
    "PULP_CBC_CMD": "cbc",
    "GUROBI_CMD": "gurobi",
    "GUROBI": "gurobi",
    "SCIP_CMD": "scip",
    "SCIP": "scip",
    "SCIP_PY": "scip",
    "HiGHS_CMD": "highs",
    "HiGHS": "highs",
}
# Execution states
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

# Databricks constants
DATABRICKS_TERMINATE_STATE = "TERMINATED"
DATABRICKS_FINISH_TO_STATE_MAP = dict(
    SUCCESS=EXEC_STATE_CORRECT,
    USER_CANCELED=EXEC_STATE_STOPPED,
)
DATABRICKS_TO_STATE_MAP = dict(
    BLOCKED=EXEC_STATE_QUEUED,
    PENDING=EXEC_STATE_QUEUED,
    QUEUED=EXEC_STATE_QUEUED,
    RUNNING=EXEC_STATE_RUNNING,
    TERMINATING=EXEC_STATE_RUNNING,
    SUCCESS=EXEC_STATE_CORRECT,
    USER_CANCELED=EXEC_STATE_STOPPED,
    OTHER_FINISH_ERROR=EXEC_STATE_ERROR,
)


class OrchError(Exception):
    status_code = 400

    def __init__(self, error=None, status_code=None, payload=None, log_txt=None):
        Exception.__init__(self, error)
        if error is not None:
            self.error = error
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        if log_txt is not None:
            self.log_txt = log_txt
        else:
            self.log_txt = self.error

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["error"] = self.error
        return rv


class AirflowError(OrchError):
    log_txt = "Airflow error"


class DatabricksError(OrchError):
    log_txt = "Databricks error"


class NoSolverException(Exception):
    pass


class BadConfiguration(Exception):
    pass


class BadInstance(Exception):
    pass


class BadSolution(Exception):
    pass


class BadInstanceChecks(Exception):
    pass


class BadSolutionChecks(Exception):
    pass


config_orchestrator = {
    "airflow": {
        "name": "Airflow",
        "def_schema": "solve_model_dag",
        "run_id": "dag_run_id",
    },
    "databricks": {
        "name": "Databricks",
        "def_schema": "979073949072767",
        "run_id": "run_id",
    },
}