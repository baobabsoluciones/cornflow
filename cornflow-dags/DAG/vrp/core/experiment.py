import pytups as pt
from cornflow_client import ExperimentCore, get_empty_schema
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    schema_checks = get_empty_schema()

    def __init__(self, instance: Instance, solution: Solution):
        super().__init__(instance, solution)
        if self.solution is None:
            self.solution = Solution(pt.SuperDict())
        return

    def solve(self, options):
        raise NotImplementedError()

    def get_objective(self):
        """
        Returns value of Objective Function
        :return:
        """
        arcs_dict = self.instance.data["arcs"]
        distance = 0
        for i in self.solution.data["routes"]:

            route = self.solution.data["routes"][i]
            route_distance = 0

            for j in range(len(route) - 1):
                route_distance += arcs_dict[(route[j], route[j + 1])]

            distance += route_distance

        return distance
        pass
