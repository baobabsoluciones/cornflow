import os

from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from pytups import TupList, SuperDict
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

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
        # if solution is empty, we return 0
        if len(self.solution.data["route"]) == 0:
            return 0
        # we get a sorted list of nodes by position
        arcs = self.solution.get_used_arcs()

        # we sum all arc weights in the solution
        return sum(self.get_used_arc_weights().values())

    def get_used_arc_weights(self) -> dict:
        arcs = self.solution.get_used_arcs()
        weight = self.instance.get_indexed_arcs()
        return arcs.to_dict(None).kapply(lambda k: weight[k]["w"])

    def check_missing_nodes(self):
        nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
        nodes_out = TupList(n["node"] for n in self.solution.data["route"]).to_set()
        return TupList({"node": n} for n in (nodes_in - nodes_out))

    def check_missing_positions(self):
        nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
        positions = TupList(n["pos"] for n in self.solution.data["route"]).to_set()
        return TupList({"position": p} for p in set(range(len(nodes_in))) - positions)

    def check_solution(self, *args, **kwargs) -> SuperDict:
        return SuperDict(
            missing_nodes=self.check_missing_nodes(),
            missing_positions=self.check_missing_positions(),
        )

    def get_report(self):
        # get positions (explicit, or implicitly via distances)
        # get graph of solution
        #
        pass
