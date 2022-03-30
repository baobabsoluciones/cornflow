from .Heuristic import Heuristic
import numpy as np


class DirectHeuristic(Heuristic):
    def solve(self, config):
        self.log += "Converting data lists to arrays\n"

        self.log += "Solver chosen : Heuristic\n"
        ratio = self.values / self.weights
        idx = ratio.argsort()[::-1]
        self.weights = self.weights[idx]
        self.values = self.values[idx]
        self.log += "Launching heuristic solver \n"

        super().solve(None)

        ordered_solution = [0] * self.instance.data["nb_objects"]
        for obj in self.solution.data["include"]:
            ordered_solution[obj["id"]] = 1
        idx2 = idx.argsort()
        ordered_solution = np.array(ordered_solution)[idx2]

        self.solution.data["include"] = []
        for i in range(self.instance.data["nb_objects"]):
            if ordered_solution[i] == 1:
                self.solution.data["include"].append({"id": i})

        self.solver = "Direct"

        return 0
