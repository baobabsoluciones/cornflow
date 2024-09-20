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
        # we want to find all the potential solutions for the sudoku
        solver.parameters.enumerate_all_solutions = True

        # we want all sudokus, in case of more than one solution
        class VarArraySolutionCollector(cp_model.CpSolverSolutionCallback):

            def __init__(self, variables):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.__variables = variables
                self.solution_list = []

            def on_solution_callback(self):
                # my_elements
                self.solution_list.append(self.__variables.vapply(self.Value))

        solution_collector = VarArraySolutionCollector(my_elements)
        termination_condition = solver.Solve(model, solution_collector)
        all_solutions = solution_collector.solution_list
        other_solutions = []
        if len(all_solutions) >= 1:
            assignment_values = solution_collector.solution_list[0]
        if len(all_solutions) > 1:
            other_solutions = solution_collector.solution_list[1:]
        if termination_condition not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return dict(
                status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )

        def solution_enc(pos, value):
            row, col = pos_to_row_col(pos, size)
            return pt.SuperDict(row=row, col=col, value=value)

        def assignment_to_solution(values: pt.SuperDict) -> pt.TupList[pt.SuperDict]:
            return (
                values.kfilter(lambda k: k not in value_per_pos)
                .kvapply(solution_enc)
                .values_tl()
            )

        def treat_others(others):
            result = pt.TupList()
            for position, solution in enumerate(others):
                values = assignment_to_solution(solution)
                values.vapply_col("id", lambda v: position)
                result.extend(values)
            return result

        self.solution = Solution.from_dict(
            dict(
                assignment=assignment_to_solution(assignment_values),
                alternatives=treat_others(other_solutions),
            )
        )

        return dict(
            status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )
