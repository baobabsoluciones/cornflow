from cornflow_client import ExperimentCore
from .instance import Instance
from .solution import Solution
from pytups import TupList, SuperDict


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
        # we get a sorted list of nodes by position
        route = (
            TupList(self.solution.data["route"])
            .sorted(key=lambda v: v["pos"])
            .vapply(lambda v: v["node"])
        )
        weight = {(el["n1"], el["n2"]): el["w"] for el in self.instance.data["arcs"]}
        # we sum all arcs in the solution
        return (
            sum([weight[n1, n2] for n1, n2 in zip(route, route[1:])])
            + weight[route[-1], route[0]]
        )

    def check_missing_nodes(self):
        nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
        nodes_out = TupList(n["node"] for n in self.solution.data["route"]).to_set()
        return {n: 1 for n in (nodes_in - nodes_out)}

    def check_missing_positions(self):
        nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
        positions = TupList(n["pos"] for n in self.solution.data["route"]).to_set()
        return {p: 1 for p in set(range(len(nodes_in))) - positions}

    def check_solution(self, *args, **kwargs) -> SuperDict:
        return SuperDict(
            missing_nodes=self.check_missing_nodes(),
            missing_positions=self.check_missing_positions(),
        )
