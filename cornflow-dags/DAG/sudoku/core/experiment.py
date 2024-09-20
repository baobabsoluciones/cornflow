from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
import pytups as pt
from .instance import Instance
from .solution import Solution
import os
import quarto
import plotnine as pn
import pandas as pd


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
        return 0

    def get_complete_solution(self, id=None):
        initial_values = self.instance.get_initial_values().vapply(pt.SuperDict)
        initial_values.vapply_col("initial", lambda v: True)
        if id is None:
            solution_values = self.solution.get_assignments(self.instance.get_size())
        else:
            solution_values = self.solution.get_others(self.instance.get_size(), id=id)
        solution_values = solution_values.vapply(pt.SuperDict)
        solution_values.vapply_col("initial", lambda v: False)
        return solution_values + initial_values

    def check_solution(self, *args, **kwargs) -> dict:

        # if we check that we have all expected values at least once in each group, it should be enough
        all_values = self.get_complete_solution()
        size = self.instance.get_size()

        expected_values = set(range(1, size + 1))
        groups = ["row", "col", "square"]
        err_all_dif = pt.SuperDict()
        for group in groups:
            err_all_dif[group] = all_values.to_dict("value", indices="row").vapply(
                lambda v: v.set_diff(expected_values)
            )
        # this returns for each group and slot, the list of missing values
        err_all_dif = err_all_dif.to_dictup().vfilter(lambda v: len(v))

        return pt.SuperDict(missing_values=err_all_dif).vfilter(lambda v: len(v))

    def generate_report(self, report_name="report") -> str:
        if not os.path.isabs(report_name):
            report_name = os.path.join(
                os.path.dirname(__file__), "../report/", report_name
            )

        return self.generate_report_quarto(quarto, report_name=report_name)

    def print(self, id=None):
        values = self.get_complete_solution(id=id)
        board = self.instance.values_to_matrix(values)
        return self.instance.generate_board(board)

    def plot(self, id=None):

        my_solution = self.get_complete_solution(id=id)
        my_table = pd.DataFrame(my_solution)
        a = pt.TupList(range(10)).vapply(lambda v: v - 0.5)
        return (
            pn.ggplot(my_table, pn.aes(x="row", y="col", fill="initial"))
            + pn.geom_tile(pn.aes(width=1, height=1))
            + pn.geom_text(pn.aes(label="value"), size=10)
            + pn.theme_void()
            # + pn.labs(fill='')
            + pn.scale_fill_manual(values=["white", "lightgreen"], guide=None)
            + pn.geom_vline(xintercept=a, color="black", size=0.5, linetype="dashed")
            + pn.geom_hline(yintercept=a, color="black", size=0.5, linetype="dashed")
            + pn.geom_vline(xintercept=[-0.5, 2.5, 5.5, 8.5], color="black", size=3)
            + pn.geom_hline(yintercept=[-0.5, 2.5, 5.5, 8.5], color="black", size=3)
            + pn.xlim(-0.5, 8.5)
            + pn.ylim(-0.5, 8.5)
        )

    def get_others(self):
        return self.solution.get_others(self.instance.get_size())
