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

PARAMETER_SOLVER_TRANSLATING_MAPPING = {
    ('bar_iter_limit', 'pyomo', 'cbc') : 'barr' ,
    ('best_obj_stop', 'pyomo', 'cbc') : 'primalT' ,
    ('cutoff', 'pyomo', 'cbc') : 'cuts' ,
    ('iteration_limit', 'pyomo', 'cbc') : 'maxIt' ,
    ('solution_limit', 'pyomo', 'cbc') : 'maxSaved' ,
    ('time_limit', 'pyomo', 'cbc') : 'sec' ,
    ('mip_gap', 'pyomo', 'cbc') : 'allow' ,
    ('optimality_tol', 'pyomo', 'cbc') : 'dualT' ,
    ('pump_passes', 'pyomo', 'cbc') : 'pumpC' ,
    ('heuristics', 'pyomo', 'cbc') : 'heur' ,

    ('is_mip', 'pulp', 'cbc') : 'mip' ,
    ('optimality_tol', 'pulp', 'cbc') : 'gapAbs' ,
    ('cutoff', 'pulp', 'cbc') : 'cuts' ,
    ('time_limit', 'pulp', 'cbc') : 'timeLimit' ,
    ('threads', 'pulp', 'cbc') : 'threads' ,
    ('presolve', 'pulp', 'cbc') : 'presolve' ,
    

    ('bar_iter_limit', 'pyomo', 'gurobi') : 'BarIterLimit' ,
    ('best_obj_stop', 'pyomo', 'gurobi') : 'BestObjStop' ,
    ('cutoff', 'pyomo', 'gurobi') : 'Cutoff' ,
    ('iteration_limit', 'pyomo', 'gurobi') : 'IterationLimit' ,
    ('mem_limit', 'pyomo', 'gurobi') : 'MemLimit' ,
    ('solution_limit', 'pyomo', 'gurobi') : 'SolutionLimit' ,
    ('time_limit', 'pyomo', 'gurobi') : 'TimeLimit' ,
    ('mip_gap', 'pyomo', 'gurobi') : 'MIPGap' ,
    ('optimality_tol', 'pyomo', 'gurobi') : 'OptimalityTol' ,
    ('feasibility_tol', 'pyomo', 'gurobi') : 'FeasibilityTol' ,
    ('branch_dir', 'pyomo', 'gurobi') : 'BranchDir' ,
    ('pump_passes', 'pyomo', 'gurobi') : 'PumpPasses' ,
    ('heuristics', 'pyomo', 'gurobi') : 'Heuristics' ,
    ('presolve', 'pyomo', 'gurobi') : 'Presolve' ,
    ('threads', 'pyomo', 'gurobi') : 'threads' ,
    
    ('is_mip', 'pulp', 'gurobi') : 'mip' ,
    ('time_limit', 'pulp', 'gurobi') : 'timeLimit' ,
    ('presolve', 'pulp', 'gurobi') : 'presolve' ,
    ('mip_gap', 'pulp', 'gurobi') : 'MIPGap' ,
    ('optimality_tol', 'pulp', 'gurobi') : 'gapAbs' ,
    ('feasibility_tol', 'pulp', 'gurobi') : 'FeasibilityTol' ,
    ('iteration_limit', 'pulp', 'gurobi') : 'IterationLimit' ,


    ('bar_tol', 'pyomo', 'scip') : 'numerics/barrierconvtol' ,
    ('cutoff_breaker', 'pyomo', 'scip') : 'heuristics/shiftandpropagate/cutoffbreaker' ,
    ('lp_iteration_limit', 'pyomo', 'scip') : 'lp/iterlim' ,
    ('mem_limit', 'pyomo', 'scip') : 'limits/memory' ,
    ('solution_limit', 'pyomo', 'scip') : 'limits/maxsol' ,
    ('time_limit', 'pyomo', 'scip') : 'limits/time' ,
    ('rel_optimality_tol', 'pyomo', 'scip') : 'limits/gap' ,
    ('lp_optimality_tol', 'pyomo', 'scip') : 'numerics/lpfeastol' ,
    ('pump_passes', 'pyomo', 'scip') : 'heuristics/feaspump/maxdepth' ,
    ('presolve', 'pyomo', 'scip') : 'presolve' ,
    ('threads', 'pyomo', 'scip') : 'threads' ,
    ('nlp_tol', 'pyomo', 'scip') : 'heuristics/subnlp/opttol' ,
    ('cutoff', 'pyomo', 'scip') : 'heuristics/subnlp/setcutoff' ,
    ('nlp_iteration_limit', 'pyomo', 'scip') : 'heuristics/subnlp/itermin' ,
    ('optimality_tol', 'pyomo', 'scip') : 'limits/absgap ' ,

    ('is_mip', 'pulp', 'scip') : 'mip' ,
    ('optimality_tol', 'pulp', 'scip') : 'gapAbs' ,
    ('rel_optimality_tol', 'pulp', 'scip') : 'gapRel' ,
    ('time_limit', 'pulp', 'scip') : 'timeLimit' ,
    ('threads', 'pulp', 'scip') : 'threads' ,
    ('max_nodes', 'pulp', 'scip') : 'maxNodes' ,
    ('lp_iteration_limit', 'pulp', 'scip') : 'lp/iterlim' ,
    ('mem_limit', 'pulp', 'scip') : 'limits/memory' ,


    ('presolve', 'pyomo', 'highs') : 'presolve' ,
    ('parallel', 'pyomo', 'highs') : 'parallel' ,
    ('crossover', 'pyomo', 'highs') : 'run_crossover' ,
    ('time_limit', 'pyomo', 'highs') : 'time_limit' ,
    ('rel_optimality_tol', 'pyomo', 'highs') : 'mip_rel_gap' ,

    ('is_mip', 'pulp', 'highs') : 'mip' ,
    ('optimality_tol', 'pulp', 'highs') : 'gapAbs' ,
    ('time_limit', 'pulp', 'highs') : 'timeLimit' ,
    ('threads', 'pulp', 'highs') : 'threads' ,
    ('rel_optimality_tol', 'pulp', 'highs') : 'gapRel' ,

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
