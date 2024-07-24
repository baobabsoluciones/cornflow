import os

from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from pytups import TupList, SuperDict
from .instance import Instance
from .solution import Solution

import json, tempfile
import quarto


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def to_dict(self) -> dict:
        return dict(instance=self.instance.to_dict(), solution=self.solution.to_dict())

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            Instance.from_dict(data["instance"]), Solution.from_dict(data["solution"])
        )

    @classmethod
    def from_json(cls, path: str) -> "Experiment":
        with open(path, "r") as f:
            data_json = json.load(f)
        return cls.from_dict(data_json)

    def to_json(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

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

    def generate_report(self, report_path: str, report_name="report") -> None:
        # a user may give the full "report.qmd" name.
        # We want to take out the extension
        path_without_ext = os.path.splitext(report_name)[0]

        # if someone gives the absolute path: we use that.
        # otherwise we assume it's a file on the report/ directory:
        if not os.path.isabs(path_without_ext):
            path_without_ext = os.path.join(
                os.path.dirname(__file__), "../report/", path_without_ext
            )
        path_to_qmd = path_without_ext + ".qmd"
        if not os.path.exists(path_to_qmd):
            raise FileNotFoundError(f"Report with path {path_to_qmd} does not exist.")
        path_to_output = path_without_ext + ".html"
        try:
            quarto.quarto.find_quarto()
        except FileNotFoundError:
            raise ModuleNotFoundError("Quarto is not installed.")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "experiment.json")
            # write a json with instance and solution to temp file
            self.to_json(path)
            # pass the path to the report to render
            # it generates a report with path = path_to_output
            quarto.render(input=path_to_qmd, execute_params=dict(file_name=path))
        # quarto always writes the report in the .qmd directory.
        # thus, we need to move it where we want to:
        os.replace(path_to_output, report_path)
