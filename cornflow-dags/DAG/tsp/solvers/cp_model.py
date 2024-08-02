from ortools.sat.python import cp_model
from cornflow_client.constants import (
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    ORTOOLS_STATUS_MAPPING,
)
from pytups import TupList, SuperDict
from ..core import Solution, Experiment


class OrToolsCP(Experiment):
    """
    The following model was taken from the ortools python examples: https://github.com/google/or-tools
    """

    def solve(self, options: dict):
        distance = (
            self.instance.get_arcs()
            .to_dict(result_col=["w"], indices=["n1", "n2"], is_list=False)
            .kfilter(lambda k: k[0] != k[1])
        )
        model = cp_model.CpModel()
        create_literal = lambda i, j: model.NewBoolVar("%i follows %i" % (j, i))
        literals = distance.kapply(lambda k: create_literal(*k))
        arcs = literals.to_tuplist()
        model.AddCircuit(arcs)

        model.Minimize(sum((literals * distance).values()))
        solver = cp_model.CpSolver()
        if options.get("msg", False):
            solver.parameters.log_search_progress = True
        # To benefit from the linearization of the circuit constraint.
        solver.parameters.linearization_level = 2
        solver.parameters.max_time_in_seconds = options.get("timeLimit", 10)
        if "threads" in options:
            solver.parameters.num_search_workers = options["threads"]

        termination_condition = solver.Solve(model)
        if options.get("msg", False):
            print(solver.ResponseStats())

        if termination_condition not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return dict(
                status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                status_sol=SOLUTION_STATUS_INFEASIBLE,
            )
        next = (
            literals.vapply(solver.BooleanValue)
            .vfilter(lambda v: v)
            .keys_tl()
            .to_dict(1, is_list=False)
        )
        first = next.keys_tl(0)
        current_node = first
        solution = TupList([first])
        while True:
            current_node = next[current_node]
            if current_node == first:
                break
            solution.append(current_node)
        nodes = solution.kvapply(lambda k, v: SuperDict(pos=k, node=v))
        self.solution = Solution(dict(route=nodes))

        return dict(
            status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )
