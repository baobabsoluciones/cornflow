import math

from ortools.sat.python import cp_model
from cornflow_client.constants import (
    ORTOOLS_STATUS_MAPPING,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)
import pytups as pt
from ..core import Solution, Experiment
from ..core.tools import pos_to_row_col


class OrToolsCP(Experiment):
    def solve(self, options: dict):
        model = cp_model.CpModel()
        initial_values = self.instance.get_initial_values()
        size = self.instance.get_size()
        value_per_pos = initial_values.to_dict("value", indices="pos", is_list=False)
        all_positions = self.instance.generate_all_positions()

        def get_var_or_number(v):

            pos = v["pos"]
            row = v["row"]
            col = v["col"]

            if pos in value_per_pos:
                return value_per_pos[v["pos"]]
            # assignment values start at 1 (e.g., 1 -> 9 in classic sudoku)
            return model.NewIntVar(lb=1, ub=size, name=f"assign_{row}_{col}")

        my_elements = all_positions.vapply(get_var_or_number)

        # unique over squares, rows, cols
        my_groups = ["square", "row", "col"]
        for group in my_groups:
            positions_per_group = all_positions.values_tl().to_dict(
                "pos", indices=group
            )
            for values in positions_per_group.values():
                model.AddAllDifferent(my_elements.filter(values).values())

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = options.get("timeLimit", 10)
        if options.get("msg"):
            solver.parameters.log_search_progress = True
        termination_condition = solver.Solve(model)
        if termination_condition not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return dict(
                status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )

        assignment_values = my_elements.vapply(solver.Value)

        def solution_enc(pos, value):
            row, col = pos_to_row_col(pos, size)
            return pt.SuperDict(row=row, col=col, value=value)

        solution_data = (
            assignment_values.kfilter(lambda k: k not in value_per_pos)
            .kvapply(solution_enc)
            .values_tl()
        )
        self.solution = Solution(dict(assignment=solution_data))

        return dict(
            status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )
