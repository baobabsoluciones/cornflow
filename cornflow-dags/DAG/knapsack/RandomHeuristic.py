from .Heuristic import Heuristic
from .core.experiment import Experiment
from timeit import default_timer as timer
import numpy as np
from random import shuffle


class RandomHeuristic(Heuristic):
    def solve(self, config):
        time_limit = config.get("timeLimit", 15)
        best_res = None
        self.log += "Converting data lists to arrays\n"

        self.log += "Solver chosen : RandomHeuristic\n"
        start = timer()

        # Direct solution
        ratio = self.values / self.weights
        idx = ratio.argsort()[::-1]
        ids = np.arange(self.instance.data["nb_objects"])
        ids = ids[idx]
        self.weights = self.weights[idx]
        self.values = self.values[idx]
        self.log += "Launching heuristic solver \n"

        super().solve(None)

        ordered_solution = [0] * self.instance.data["nb_objects"]
        for obj in self.solution.data["include"]:
            ordered_solution[obj["id"]] = 1
        idx2 = idx.argsort()
        ordered_solution = np.array(ordered_solution)[idx2]

        self.solution.data["include"] = [
            {"id": i}
            for i in range(self.instance.data["nb_objects"])
            if ordered_solution[i] == 1
        ]

        best_res = self.solution.copy()
        self.solution.data["include"] = []

        idx2 = idx.argsort()
        self.weights = self.weights[idx2]
        self.values = self.values[idx2]

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

            self.solution.data["include"] = [
                {"id": i}
                for i in range(self.instance.data["nb_objects"])
                if ordered_solution[i] == 1
            ]

            if (
                Experiment.cls_objective_function(self.instance, best_res)
                < self.objective_function()
            ):
                best_res = self.solution.copy()

            self.solution.data["include"] = []

        self.solver = "RandomHeuristic"
        self.solution = best_res

        return 0
