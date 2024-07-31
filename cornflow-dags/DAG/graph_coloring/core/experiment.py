from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from pytups import TupList
from .instance import Instance
from .solution import Solution
import os
import quarto


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    @property
    def instance(self) -> Instance:
        return super().instance

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            Instance.from_dict(data["instance"]), Solution.from_dict(data["solution"])
        )

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
        nodes = self.instance.get_nodes()
        missing_colors = TupList(set(nodes) - colors.keys())
        errors = [
            {"n1": n1, "n2": n2}
            for (n1, n2) in pairs
            if n1 in colors and n2 in colors and colors[n1] == colors[n2]
        ]
        return dict(pairs=errors, missing=missing_colors)

    def generate_report(self, report_path: str, report_name="report") -> None:
        if not os.path.isabs(report_name):
            report_name = os.path.join(
                os.path.dirname(__file__), "../report/", report_name
            )

        return self.generate_report_quarto(
            quarto, report_path=report_path, report_name=report_name
        )
