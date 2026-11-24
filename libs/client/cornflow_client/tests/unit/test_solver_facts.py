from unittest import TestCase

from cornflow_client import (
    ApplicationCore,
    InstanceCore,
    get_empty_schema,
    ExperimentCore,
    SolutionCore,
)
from cornflow_client.constants import STATUS_OPTIMAL, SOLUTION_STATUS_FEASIBLE


class Solution(SolutionCore):
    schema = get_empty_schema(properties=dict(x=dict(type="number")))


class Instance(InstanceCore):
    schema = get_empty_schema(properties=dict(x=dict(type="number")))
    schema_checks = get_empty_schema()


class BaseSolver(ExperimentCore):
    schema_checks = get_empty_schema()
    reported = None

    def solve(self, options):
        self.solution = Solution({"x": 1})
        return dict(
            status=STATUS_OPTIMAL,
            status_sol=SOLUTION_STATUS_FEASIBLE,
            **(self.reported or {}),
        )

    def get_objective(self):
        return 0

    def check_solution(self, *args, **kwargs):
        return dict()


def make_app(solver_class):
    class App(ApplicationCore):
        name = "facts"
        instance = Instance
        solution = Solution
        solvers = dict(default=solver_class)
        schema = get_empty_schema(properties=dict(), solvers=["default"])

        @property
        def test_cases(self):
            return [{}]

    return App()


def solve_log(solver_class):
    return make_app(solver_class).solve({"x": 1}, dict(solver="default"))[-1]


class TestSolverFacts(TestCase):
    def test_reported_in_return_value(self):
        class Solver(BaseSolver):
            reported = dict(
                objective=100.0, best_bound=90.0, nodes=1200, iterations=5000
            )

        log = solve_log(Solver)
        self.assertEqual(log["objective"], 100.0)
        self.assertEqual(log["best_bound"], 90.0)
        self.assertEqual(log["nodes"], 1200)
        self.assertEqual(log["iterations"], 5000)
        # relative gap derived from objective and best bound
        self.assertAlmostEqual(log["gap"], 0.1)
        # today's keys are still there
        self.assertEqual(log["status"], "Optimal")
        self.assertEqual(log["solver"], "default")
        self.assertIn("time", log)

    def test_reported_in_attribute(self):
        class Solver(BaseSolver):
            def solve(self, options):
                self.solver_facts = dict(objective=10, best_bound=10, nodes=3)
                return super().solve(options)

        log = solve_log(Solver)
        self.assertEqual(log["objective"], 10.0)
        self.assertEqual(log["gap"], 0.0)
        self.assertEqual(log["nodes"], 3)

    def test_gap_with_a_zero_objective(self):
        class Proven(BaseSolver):
            reported = dict(objective=0, best_bound=0)

        class Open(BaseSolver):
            reported = dict(objective=0, best_bound=5.0)

        # objective and bound both 0: proven optimal, no gap
        self.assertEqual(solve_log(Proven)["gap"], 0.0)
        # a relative gap over a zero objective is undefined: left out, the facts stay
        log = solve_log(Open)
        self.assertNotIn("gap", log)
        self.assertEqual(log["best_bound"], 5.0)

    def test_reported_gap_is_kept(self):
        class Solver(BaseSolver):
            reported = dict(objective=100.0, best_bound=90.0, gap=0.25)

        self.assertEqual(solve_log(Solver)["gap"], 0.25)

    def test_invalid_facts_are_dropped(self):
        class Solver(BaseSolver):
            reported = dict(
                objective=float("nan"), best_bound=float("inf"), nodes="many", gap=True
            )

        log = solve_log(Solver)
        for key in ("objective", "best_bound", "nodes", "gap", "iterations"):
            self.assertNotIn(key, log)

    def test_nothing_reported_keeps_todays_log(self):
        log = solve_log(BaseSolver)
        self.assertEqual(
            set(log),
            {"status", "status_sol", "status_code", "sol_code", "time", "solver"},
        )
