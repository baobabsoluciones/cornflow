from .core import Solution
from .core import Experiment
import numpy as np


class DynamicSolver(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"include": []})
        super().__init__(instance, solution)
        self.log += "Initialized\n"

    def solve(self, config):
        self.log += "Converting data lists to arrays\n"
        self.weights = np.array(self.instance.data["weights"])
        self.values = np.array(self.instance.data["values"])

        self.log += "Solver chosen : Dynamic\n"
        idx = self.weights.argsort()
        self.weights = self.weights[idx]
        self.values = self.values[idx]

        self.log += "Launching dynamic solver \n"
        res = self.dyn_solver()
        self.log += "Sorting the final arrays\n"
        idx2 = idx.argsort()
        res["include"] = (np.array(res["include"])[idx2]).tolist()
        self.solver = "Dynamic"

        for i in range(len(res["include"])):
            if res["include"][i] == 1:
                self.solution.data["include"].append({"id": i})

        return 1

    def dyn_solver(self):  #
        U = np.zeros(
            (
                self.instance.data["nb_objects"],
                self.instance.data["weight_capacity"] + 1 - self.weights[0],
                2,
            )
        )  # self.instance.data["weight_capacity"]
        self.log += "Initializing the table\n"
        ## U[i, j, 0] : solution of the problem for the i first items and a backpack of capacity j
        ## U[i, j, 1] : 0 if the item number i is not taken, 1 if it is.
        for j in range(0, self.instance.data["weight_capacity"] + 1 - self.weights[0]):
            U[0, j, 0] = self.values[0]
            U[0, j, 1] = 1

        self.log += "Filling table U\n"
        ## Filling the table U. For each (i, j), U(i, j) = V(i, j + w0).
        for i in range(1, self.instance.data["nb_objects"]):
            for j in range(
                0, self.instance.data["weight_capacity"] + 1 - self.weights[0]
            ):
                if j + self.weights[0] < self.weights[i]:
                    U[i, j, 0] = U[i - 1, j, 0]
                    U[i, j, 1] = 0
                elif (j + self.weights[0] == self.weights[i]) or (
                    j + self.weights[0] - self.weights[i] < self.weights[0]
                ):
                    U[i, j, 0] = max(U[i - 1, j, 0], self.values[i])
                    if U[i - 1, j, 0] >= self.values[i]:
                        U[i, j, 1] = 0
                    else:
                        U[i, j, 1] = 1
                else:
                    U[i, j, 0] = max(
                        U[i - 1, j, 0],
                        U[i - 1, j - self.weights[i], 0] + self.values[i],
                    )
                    if (
                        U[i - 1, j, 0]
                        >= U[i - 1, j - self.weights[i], 0] + self.values[i]
                    ):
                        U[i, j, 1] = 0
                    else:
                        U[i, j, 1] = 1

        res_dict = dict()
        res_dict["include"] = [0] * self.instance.data["nb_objects"]

        self.log += "Tracing back\n"
        ## Tracing back from the end of the tab to the top to get all the included items
        index_v = self.instance.data["weight_capacity"] - self.weights[0]
        for i in range(self.instance.data["nb_objects"] - 1, -1, -1):
            if U[i, index_v, 1] == 1 and index_v >= 0:
                index_v = index_v - self.weights[i]
                res_dict["include"][i] = 1

                # res_dict["weight"] += self.weights[i]
                # res_dict["value"] += self.values[i]
        self.log += "Solving complete\n"
        return res_dict
