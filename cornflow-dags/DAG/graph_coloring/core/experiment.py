from cornflow_client import ExperimentCore
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value):
        self._solution = value

    def get_objective(self) -> float:
        return self.solution.get_assignments().values_tl().unique().len()

    def check_solution(self, *args, **kwargs) -> dict:
        # if a pair of nodes have the same colors: that's a problem
        colors = self.solution.get_assignments()
        pairs = self.instance.get_pairs()
        errors = {(n1, n2): 1 for (n1, n2) in pairs if colors[n1] == colors[n2]}
        return dict(pairs=errors)
