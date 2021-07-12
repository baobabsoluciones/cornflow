from .solution import Solution


class Experiment:
    def __init__(self, instance, solution):
        self.instance = instance
        if solution is None:
            solution = Solution(dict())
        self.solution = solution

    def check_solution(self):
        if len(self.solution.data) != 0:
            return self.check_total_weight()
        else:
            raise NotImplementedError("No solution to check")

    def check_total_weight(self):

        total_weight = 0
        for i in range(len(self.instance.data["values"])):
            total_weight = (
                self.solution.data["include"][i] * self.instance.data["weights"][i]
            )

        if (
            total_weight == self.solution.data["weight"]
            and total_weight <= self.instance.data["weight_capacity"]
        ):
            return True

        return False

    def objective_function(self):
        total_value = 0
        if "include" not in self.solution.data:
            return -1
        for obj in self.solution.data["include"]:
            total_value += self.instance.data["values"][obj["id"]]
        return total_value

    @classmethod
    def cls_objective_function(cls, instance, solution):
        total_value = 0
        if "include" not in solution.data:
            return -1
        for obj in solution.data["include"]:
            total_value += instance.data["values"][obj["id"]]
        return total_value
