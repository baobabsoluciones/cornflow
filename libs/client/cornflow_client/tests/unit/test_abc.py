from cornflow_client import (
    InstanceCore,
    SolutionCore,
    ApplicationCore,
    ExperimentCore,
    get_empty_schema,
)
from cornflow_client.constants import BadConfiguration, BadInstance
import unittest


class TestABC(unittest.TestCase):
    def test_good_solution(self):
        GoodSolutionClass(dict(a=1))

    def test_bad_solution(self):
        must_fail = lambda: BadSolutionClass(dict(a=1))
        self.assertRaises(TypeError, must_fail)

    def test_good_instance(self):
        GoodInstanceClass(dict(a=1))

    def test_bad_instance(self):
        must_fail = lambda: BadInstanceClass(dict(a=1))
        self.assertRaises(TypeError, must_fail)

    def test_experiment(self):
        GoodExperiment(GoodInstanceClass(dict()), GoodSolutionClass(dict()))

    def test_bad_experiment(self):
        must_fail = lambda: BadExperiment(
            GoodInstanceClass(dict()), GoodSolutionClass(dict())
        )
        self.assertRaises(TypeError, must_fail)

    def test_good_application(self):
        GoodApp().get_solver("default")

    def test_good_application_solver(self):
        solver = ConcatenatedSolver().get_solver("pulp")
        self.assertIsNotNone(solver)

    def test_good_application_solver_none(self):
        solver = ConcatenatedSolver().get_solver("pulp1")
        self.assertIsNone(solver)

    def test_bad_application(self):
        must_fail = lambda: BadApp()
        self.assertRaises(TypeError, must_fail)

    def test_bad_configuration(self):
        must_fail = lambda: GoodApp().solve(
            data=dict(number=1), config=dict(timeLimit="")
        )
        self.assertRaises(BadConfiguration, must_fail)

    def test_incorrect_good_instance(self):
        must_fail = lambda: GoodApp().solve(data=dict(number=""), config=dict())
        self.assertRaises(BadInstance, must_fail)

    def test_check_data(self):
        inst_check, sol_check, log = GoodApp().check(dict(number=""), dict())
        self.assertIsInstance(inst_check, dict)
        self.assertIsInstance(sol_check, dict)
        self.assertIsInstance(log, dict)
        self.assertEqual(log.get('status'), "Optimal")


class GoodInstanceClass(InstanceCore):
    schema = get_empty_schema(dict(number=dict(type="number")))
    schema_checks = get_empty_schema()

    def check(self) -> dict:
        return dict()


class BadInstanceClass(InstanceCore):
    @classmethod
    def from_dict(cls, data: dict) -> "BadInstanceClass":
        return cls(data)


class GoodSolutionClass(SolutionCore):
    schema = get_empty_schema()


class BadSolutionClass(SolutionCore):
    @classmethod
    def from_dict(cls, data: dict) -> "BadSolutionClass":
        return cls(data)


class GoodExperiment(ExperimentCore):
    schema_checks = get_empty_schema()

    def solve(self, options: dict):
        return dict(sol_status=1, status=1)

    def get_objective(self) -> float:
        return 1

    def check_solution(self, *args, **kwargs) -> dict:
        return dict()


class BadExperiment(ExperimentCore):
    def solve(self, options) -> dict:
        return dict()


class GoodApp(ApplicationCore):
    name = "123"
    instance = GoodInstanceClass
    solution = GoodSolutionClass
    solvers = dict(default=GoodExperiment)
    schema = get_empty_schema(dict(timeLimit=dict(type="number")), solvers=["default"])
    test_cases = [dict()]


class ConcatenatedSolver(ApplicationCore):
    name = "123"
    instance = GoodInstanceClass
    solution = GoodSolutionClass
    solvers = dict(pulp=GoodExperiment)
    schema = get_empty_schema(dict(timeLimit=dict(type="number")), solvers=["pulp.cbc"])
    test_cases = [dict()]


class BadApp(ApplicationCore):
    name = "123"
    solvers = dict(default=GoodExperiment)
