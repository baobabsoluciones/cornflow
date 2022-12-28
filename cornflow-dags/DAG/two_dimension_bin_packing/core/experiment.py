import os
from typing import Dict

from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from matplotlib import pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from pytups import SuperDict
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def __init__(self, instance: Instance, solution: Solution = None) -> None:
        ExperimentCore.__init__(self, instance=instance, solution=solution)
        if solution is None:
            self.solution = Solution(SuperDict(included=list()))

    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value):
        self._solution = value

    def solve(self, options: dict) -> dict:
        raise NotImplementedError()

    def get_objective(self) -> float:
        return 0

    def check_solution(self, *args, **kwargs) -> Dict[str, Dict]:
        return dict()

    def plot_solution(self):
        rectangles = [
            Rectangle(
                (el["x"], el["y"]),
                self.instance.get_item_width(el["id"]),
                self.instance.get_item_height(el["id"]),
            )
            for el in self.solution.data["included"]
        ]

        pc = PatchCollection(rectangles, facecolor="gray", edgecolor="black")

        fig, ax = plt.subplots(1)
        ax.add_collection(pc)
        ax.autoscale_view()
        plt.show()
