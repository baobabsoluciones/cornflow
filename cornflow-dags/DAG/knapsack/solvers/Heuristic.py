from ..core import Solution
from ..core import Experiment
import numpy as np
from cornflow_client.constants import (
    STATUS_FEASIBLE,
    SOLUTION_STATUS_FEASIBLE
)


class Heuristic(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"include": []})
        Experiment.__init__(self, instance, solution)
        self.log += "Initialized\n"
        self.weights = np.array(self.instance.data["weights"])
        self.values = np.array(self.instance.data["values"])
        self.solver = "Basic"

    def solve(self, config):
        total_weight = 0

        min_weight_obj = min(self.weights)
        self.log += "Inserting the objects one by one\n"
        i = 0
        while (
            i < len(self.weights)
            and min_weight_obj < self.instance.data["weight_capacity"] - total_weight
        ):
            if self.weights[i] + total_weight <= self.instance.data["weight_capacity"]:
                total_weight += self.weights[i]
                self.solution.data["include"].append(dict(id=i))
            i += 1

        self.log += "Solving complete\n"
        return dict(
            status=STATUS_FEASIBLE,
            status_sol=SOLUTION_STATUS_FEASIBLE
        )
