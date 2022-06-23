import time
from cornflow_client import get_empty_schema
from cornflow_client import ApplicationCore, InstanceCore, SolutionCore, ExperimentCore
from cornflow_client.constants import SOLUTION_STATUS_FEASIBLE, STATUS_OPTIMAL
from typing import Dict, List

class Instance(InstanceCore):
    schema = get_empty_schema()
    schema_checks = get_empty_schema()


class Solution(SolutionCore):
    schema = get_empty_schema()


class Solver(ExperimentCore):
    schema_checks = get_empty_schema()

    def solve(self, options):
        seconds = options.get("seconds", 60)
        seconds = options.get("timeLimit", seconds)

        print("sleep started for {} seconds".format(seconds))
        time.sleep(seconds)
        print("sleep finished")
        self.solution = Solution({})
        return dict(status=STATUS_OPTIMAL, status_sol=SOLUTION_STATUS_FEASIBLE)

    def get_objective(self) -> float:
        return 0

    def check_solution(self, *args, **kwargs):
        return dict()


class Timer(ApplicationCore):
    name = "timer"
    instance = Instance
    solution = Solution
    solvers = dict(default=Solver)
    schema = get_empty_schema(
        properties=dict(seconds=dict(type="number"), timeLimit=dict(type="number")),
        solvers=list(solvers.keys()),
    )

    @property
    def test_cases(self) -> List[Dict]:
        return list()
