from ortools.sat.python import cp_model
from cornflow_client.constants import (
    ORTOOLS_STATUS_MAPPING,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)
import pytups as pt
from ..core import Solution, Experiment


class OrToolsCP(Experiment):
    def solve(self, options: dict):
        model = cp_model.CpModel()
        input_data = pt.SuperDict.from_dict(self.instance.data)
        pairs = input_data["pairs"]
        n1s = pt.TupList(pairs).vapply(lambda v: v["n1"])
        n2s = pt.TupList(pairs).vapply(lambda v: v["n2"])
        nodes = (n1s + n2s).unique2()
        max_colors = len(nodes) - 1

        # variable declaration:
        color = pt.SuperDict(
            {
                node: model.NewIntVar(0, max_colors, "color_{}".format(node))
                for node in nodes
            }
        )
        # TODO: identify maximum cliques and apply constraint on the cliques instead of on pairs
        for pair in pairs:
            model.Add(color[pair["n1"]] != color[pair["n2"]])

        obj_var = model.NewIntVar(0, max_colors, "total_colors")
        model.AddMaxEquality(obj_var, color.values())
        model.Minimize(obj_var)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = options.get("timeLimit", 10)
        termination_condition = solver.Solve(model)
        if termination_condition not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return dict(
                status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )
        color_sol = color.vapply(solver.Value)

        assign_list = color_sol.items_tl().vapply(lambda v: dict(node=v[0], color=v[1]))
        self.solution = Solution(dict(assignment=assign_list))

        return dict(
            status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )
