from typing import  Union, Type
from cornflow_client import ApplicationCore, get_empty_schema
import os
from .core import Instance, Solution, Experiment
from .solvers import DirectHeuristic, DynamicSolver, RandomHeuristic, MIPSolver
from .parameters import threshold


class Knapsack(ApplicationCore):
    name = "knapsack"
    instance = Instance
    solution = Solution
    solvers = dict(
        Dynamic=DynamicSolver,
        Direct=DirectHeuristic,
        Random=RandomHeuristic,
        MIP=MIPSolver,
    )
    schema = get_empty_schema(
        properties=dict(timeLimit=dict(type="number")), solvers=list(solvers.keys()) + ["MIP.cbc"],
    )

    def get_solver_name(self, data, conf):
        solver_name = conf.get("solver", "Direct")
        if (
            data["parameters"]["nb_objects"] * data["parameters"]["weight_capacity"]
            > threshold
            and solver_name == "Dynamic"
        ):
            solver_name = "Direct"
        return solver_name

    def solve(self, data, conf):
        solver_name = self.get_solver_name(data, conf)
        conf["solver"] = solver_name

        return super().solve(data, conf)

    @property
    def test_cases(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(cwd, "Data", "ks_4_0")

        data = Instance.from_file(path).to_dict()
        return [data]

    def get_solver(self, name: str = "default") -> Union[Type[Experiment], None]:
        if "." in name:
            solver, _ = name.split(".")
        else:
            solver = name
        return self.solvers.get(solver)
