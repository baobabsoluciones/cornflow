from typing import List, Dict, Tuple, Union, Type

from cornflow_client import (
    ApplicationCore,
    InstanceCore,
    SolutionCore,
    ExperimentCore,
    get_pulp_jsonschema,
    get_empty_schema,
)
from cornflow_client.constants import (
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    PULP_STATUS_MAPPING,
)
import cornflow_client.airflow.dag_utilities as utils

import pulp as pl
import orloge as ol
import os

config = get_pulp_jsonschema("solver_config.json")

config["properties"]["solver"]["enum"] = pl.listSolvers()
config["properties"]["solver"]["default"] = "PULP_CBC_CMD"


class Instance(InstanceCore):
    schema = get_pulp_jsonschema()
    schema_checks = get_empty_schema()


class Solution(SolutionCore):
    schema = get_pulp_jsonschema()


class PuLPSolve(ExperimentCore):
    schema_checks = get_empty_schema()

    def solve(self, options: dict):
        options = dict(options)
        options["msg"] = 0
        if "solver" not in options:
            options["solver"] = "PULP_CBC_CMD"
        try:
            solver = pl.getSolverFromDict(options)
        except pl.PulpSolverError:
            raise utils.NoSolverException("Missing solver attribute")
        if solver is None or not solver.available():
            raise utils.NoSolverException("Solver {} is not available".format(solver))

        _vars, model = pl.LpProblem.fromDict(self.instance.data)
        model.solve(solver)
        if model.status not in [pl.LpStatusOptimal]:
            return dict(
                status=PULP_STATUS_MAPPING[model.status],
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )

        self.solution = Solution(model.toDict())
        return dict(
            status=PULP_STATUS_MAPPING[model.status],
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )

    def get_objective(self) -> float:
        _, model = pl.LpProblem.fromDict(self.solution.data)
        return model.objective


class PuLP(ApplicationCore):
    name = "solve_model_dag"
    instance = Instance
    solution = Solution
    solvers = dict(default=PuLPSolve)
    schema = config

    @property
    def test_cases(self) -> List[Dict]:
        prob = pl.LpProblem("test_export_dict_MIP", pl.LpMinimize)
        x = pl.LpVariable("x", 0, 4)
        y = pl.LpVariable("y", -1, 1)
        z = pl.LpVariable("z", 0, None, pl.LpInteger)
        prob += x + 4 * y + 9 * z, "obj"
        prob += x + y <= 5, "c1"
        prob += x + z >= 10, "c2"
        prob += -y + z == 7.5, "c3"

        return [
            {
                "name": "Base case with 3 variables",
                "instance": prob.toDict(),
                "description": "Simple MIP with 3 variables",
            }
        ]

    def get_solver(self, name: str = "default") -> Union[Type[ExperimentCore], None]:
        return PuLPSolve

    def solve(
        self, data: dict, config: dict, solution_data: dict = None
    ) -> Tuple[Dict, Union[Dict, None], Union[Dict, None], str, Dict]:
        # we overwrite the logPath argument before solving.
        log_path = config["logPath"] = "temp.log"
        algo = PuLPSolve(Instance.from_dict(data), None)
        simple_log = algo.solve(config)
        solution = algo.solution.to_dict()

        with open(log_path, "r") as f:
            log = f.read()

        # we convert the log into orloge json
        equivs = dict(
            CPLEX_CMD="CPLEX",
            CPLEX_PY="CPLEX",
            CPLEX_DLL="CPLEX",
            GUROBI="GUROBI",
            GUROBI_CMD="GUROBI",
            PULP_CBC_CMD="CBC",
            COIN_CMD="CBC",
        )
        solver_name = equivs.get(config["solver"])
        log_dict = simple_log
        if solver_name:
            try:
                # we parse the log from the solver file
                log_dict = ol.get_info_solver(
                    path=log, solver=solver_name, get_progress=True, content=True
                )
            except:
                # we keep the original log from the solve function
                log_dict = simple_log
            else:
                log_dict["progress"] = (
                    log_dict["progress"].fillna("").to_dict(orient="list")
                )

        try:
            os.remove(log_path)
        except:
            pass

        return solution, {}, {}, log, log_dict
