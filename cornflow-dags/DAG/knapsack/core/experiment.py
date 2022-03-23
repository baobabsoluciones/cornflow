from .solution import Solution
from .instance import Instance
from cornflow_client import ExperimentCore


class Experiment(ExperimentCore):
    def __init__(self, instance: Instance, solution: Solution):
        if solution is None:
            solution = Solution(dict(include=[]))
        super().__init__(instance, solution)

    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value):
        self._solution = value

    def check_solution(self):
        return self.check_total_weight()

    def check_total_weight(self):
        id_weight = self.instance.get_objects_weights()
        capacity = self.instance.get_weight_capacity()
        total_weight = sum(id_weight[el] for el in self.solution.get_ids())
        dif = capacity - total_weight
        if dif < 0:
            return dict(weight=dif)
        return dict()

    def get_objective(self):
        id_value = self.instance.get_objects_values()
        return sum(id_value[el] for el in self.solution.get_ids())

    def solve(self, options):
        raise NotImplementedError()
