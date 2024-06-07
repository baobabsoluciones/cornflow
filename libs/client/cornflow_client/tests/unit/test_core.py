import logging
import time
from unittest import TestCase

from jsonschema import Draft7Validator
from pytups import SuperDict

from cornflow_client import (
    ApplicationCore,
    InstanceCore,
    get_empty_schema,
    ExperimentCore,
    SolutionCore,
    SchemaManager,
)
from cornflow_client.constants import (
    STATUS_OPTIMAL,
    SOLUTION_STATUS_FEASIBLE,
    NoSolverException,
    BadSolution,
)


class TestCore(TestCase):
    def setUp(self):
        class DummyInstance(InstanceCore):
            schema = get_empty_schema(properties=dict(seconds=dict(type="number")))
            schema_checks = get_empty_schema(
                properties=dict(check=dict(type="array", objects=dict(type="number")))
            )

            def check(self):
                return dict(check=[1]) if self.data.get("seconds", 1) == 2 else dict()

        class DummySolution(SolutionCore):
            schema = get_empty_schema(properties=dict(sleep=dict(type="number")))

        class DummySolver(ExperimentCore):
            schema_checks = get_empty_schema()

            def solve(self, options):
                seconds = options.get("seconds", 60)
                seconds = options.get("timeLimit", seconds)

                logging.info(f"sleep started for {seconds} seconds")
                time.sleep(seconds)
                logging.info("sleep finished")
                self.solution = DummySolution({"sleep": seconds})
                return dict(status=STATUS_OPTIMAL, status_sol=SOLUTION_STATUS_FEASIBLE)

            def get_objective(self) -> float:
                return 0

            def check_solution(self, *args, **kwargs):
                return dict()

        class DummierSolver(DummySolver):
            def solve(self, options):
                return 1

        class DummyApp(ApplicationCore):
            name = "timer"
            instance = DummyInstance
            solution = DummySolution
            solvers = dict(
                default=DummySolver,
                dummier=DummierSolver,
            )
            schema = get_empty_schema(
                properties=dict(
                    seconds=dict(type="number"), timeLimit=dict(type="number")
                ),
                solvers=list(solvers.keys()),
            )

            @property
            def test_cases(self):
                return [({"seconds": 1}, {}), {"seconds": 2}]

        self.instance = DummyInstance({})
        self.solver = DummySolver(self.instance)
        self.app = DummyApp()

        self.config = SuperDict(msg=False, timeLimit=1, solver="default", seconds=10)

    def tearDown(self):
        pass

    def test_application_solve(self):
        tests = self.app.test_cases
        for pos, data in enumerate(tests):
            data_out = None
            if isinstance(data, tuple):
                # sometimes we have input and output
                data, data_out = data
            marshm = SchemaManager(self.app.instance.schema).jsonschema_to_flask()
            marshm().load(data)
            if data_out is not None:
                (
                    solution_data,
                    solution_check,
                    inst_check,
                    log,
                    log_dict,
                ) = self.app.solve(data, self.config, data_out)
            else:
                # for compatibility with previous format
                (
                    solution_data,
                    solution_check,
                    inst_check,
                    log,
                    log_dict,
                ) = self.app.solve(data, self.config)

            instance = self.app.instance.from_dict(data)

            if inst_check != {}:
                validator = Draft7Validator(instance.schema_checks)
                if not validator.is_valid(inst_check):
                    raise Exception("The instance checks have invalid format")
                continue

            if solution_data is None:
                raise ValueError("No solution found")
            marshm = SchemaManager(self.app.solution.schema).jsonschema_to_flask()
            validator = Draft7Validator(self.app.solution.schema)
            if not validator.is_valid(solution_data):
                raise Exception("The solution has invalid format")

            self.assertTrue(len(solution_data) > 0)

            solution = self.app.solution.from_dict(solution_data)
            s = self.app.get_default_solver_name()
            experim = self.app.get_solver(s)(instance, solution)
            checks = experim.check_solution()
            if len(checks) > 0:
                print(
                    f"Test instance with position {pos} failed with the following checks:"
                )
                for check in checks:
                    print(check)
            experim.get_objective()

            validator = Draft7Validator(experim.schema_checks)
            if not validator.is_valid(solution_check):
                raise Exception("The solution checks have invalid format")

    def test_solver_config(self):
        self.solver.get_solver_config(self.config)

    def test_second_solver(self):
        self.config["solver"] = "dummier"
        self.app.solve({}, self.config)

    def test_even_dummier_solver(self):
        self.assertRaises(
            BadSolution, self.app.solve, {}, self.config, {"sleep": "SOME TEXT"}
        )

    def test_get_schemas(self):
        schemas = self.app.get_schemas()
        self.assertTrue(len(schemas) > 0)
        self.assertTrue("instance" in schemas)
        self.assertTrue("solution" in schemas)
        self.assertTrue("config" in schemas)
        self.assertTrue("instance_checks" in schemas)
        self.assertTrue("solution_checks" in schemas)
        self.assertEqual(schemas["solution_checks"], get_empty_schema())

    def test_notify(self):
        self.assertFalse(self.app.notify)
