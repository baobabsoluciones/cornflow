from .Heuristic import Heuristic
from .core.experiment import Experiment
from .core.solution import Solution
from timeit import default_timer as timer
import numpy as np
from random import shuffle


class RandomHeuristic(Heuristic):
    def solve(self, config):
        time_limit = config.get("time_limit", 15)
        best_res = None
        self.log += "Converting data lists to arrays\n"

        self.log += "Solver chosen : RandomHeuristic\n"

        start = timer()
        ids = np.arange(self.instance.data["nb_objects"])
        shuf = np.arange(self.instance.data["nb_objects"])

        while timer() - start < time_limit:
            shuffle(shuf)
            self.weights = self.weights[shuf]
            self.values = self.values[shuf]
            ids = ids[shuf]
            self.log += "Launching heuristic solver \n"

            super().solve(None)
            ordered_solution = [0] * self.instance.data["nb_objects"]
            for obj in self.solution.data["include"]:
                ordered_solution[obj["id"]] = 1
            idx = ids.argsort()
            ordered_solution = np.array(ordered_solution)[idx]

            self.solution.data["include"] = []
            for i in range(self.instance.data["nb_objects"]):
                if ordered_solution[i] == 1:
                    self.solution.data["include"].append({"id": i})

            if best_res is not None:
                if (
                    Experiment.cls_objective_function(self.instance, best_res)
                    < self.objective_function()
                ):
                    best_res = Solution(dict(include=self.solution.data["include"]))
            else:
                best_res = Solution(dict(include=self.solution.data["include"]))

            self.solution.data["include"] = []

        self.solver = "RandomHeuristic"
        self.solution = best_res

        return 0
