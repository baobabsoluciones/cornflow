from cornflow_client import InstanceCore, SolutionCore, ApplicationCore, ExperimentCore
import unittest


class TestABC(unittest.TestCase):
    def test_good_solution(self):
        GoodSolution(dict(a=1))

    def test_bad_solution(self):
        must_fail = lambda: BadSolution(dict(a=1))
        self.assertRaises(TypeError, must_fail)

    def test_good_instance(self):
        GoodInstance(dict(a=1))

    def test_bad_instance(self):
        must_fail = lambda: BadInstance(dict(a=1))
        self.assertRaises(TypeError, must_fail)

    def test_experiment(self):
        GoodExperiment(GoodInstance(dict()), GoodSolution(dict()))

    def test_bad_experiment(self):
        must_fail = lambda: BadExperiment(GoodInstance(dict()), GoodSolution(dict()))
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


class GoodInstance(InstanceCore):
    def schema(self):
        return dict()


class BadInstance(InstanceCore):
    @classmethod
    def from_dict(cls, data: dict) -> "BadInstance":
        return cls(data)


class GoodSolution(SolutionCore):
    def schema(self):
        return dict()


class BadSolution(SolutionCore):
    @classmethod
    def from_dict(cls, data: dict) -> "BadSolution":
        return cls(data)


class GoodExperiment(ExperimentCore):
    def solve(self, options: dict):
        raise NotImplementedError()

    def get_objective(self) -> float:
        raise NotImplementedError()

    def check_solution(self, *args, **kwargs) -> dict:
        return dict()


class BadExperiment(ExperimentCore):
    def solve(self, options) -> dict:
        return dict()


class GoodApp(ApplicationCore):
    name = "123"
    instance = GoodInstance
    solution = GoodSolution
    solvers = dict(default=GoodExperiment)
    schema = dict(default="pulp")
    test_cases = [dict()]


class ConcatenatedSolver(ApplicationCore):
    name = "123"
    instance = GoodInstance
    solution = GoodSolution
    solvers = dict(pulp=GoodExperiment)
    schema = dict(pulp="default.cbc")
    test_cases = [dict()]


class BadApp(ApplicationCore):
    name = "123"
    solvers = dict(default=GoodExperiment)
