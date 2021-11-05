import time
from cornflow_client import get_empty_schema
from cornflow_client import ApplicationCore, InstanceCore, SolutionCore, ExperimentCore
from cornflow_client.constants import SOLUTION_STATUS_FEASIBLE, STATUS_OPTIMAL


class Instance(InstanceCore):
    schema = get_empty_schema()


class Solution(SolutionCore):
    schema = get_empty_schema()


class Solver(ExperimentCore):
    def solve(self, options):
        seconds = options.get("seconds", 60)
        seconds = options.get("timeLimit", seconds)

        print("sleep started for {} seconds".format(seconds))
        time.sleep(seconds)
        print("sleep finished")
        self.solution = Solution({})
        return dict(status=STATUS_OPTIMAL, status_sol=SOLUTION_STATUS_FEASIBLE)


class Timer(ApplicationCore):
    name = "timer"
    schema = get_empty_schema(
        dict(seconds=dict(type="number"), timeLimit=dict(type="number"))
    )
    instance = Instance
    solution = Solution
    solvers = [dict(default=Solver)]

    def test_cases(self):
        return []
