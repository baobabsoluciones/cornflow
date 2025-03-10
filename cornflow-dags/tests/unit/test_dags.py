import os
import sys

prev_dir = os.path.join(os.path.dirname(__file__), "../../DAG")
sys.path.insert(1, prev_dir)
import unittest
from unittest.mock import patch, Mock, MagicMock

# we mock everything that's airflow related:
mymodule = MagicMock()
sys.modules["airflow"] = mymodule
sys.modules["airflow.operators.python"] = mymodule
sys.modules["airflow.models"] = mymodule
sys.modules["airflow.secrets.environment_variables"] = mymodule

from cornflow_client import SchemaManager, ApplicationCore
from cornflow_client.airflow.dag_utilities import cf_solve
from jsonschema import Draft7Validator
from pytups import SuperDict


class BaseDAGTests:
    class SolvingTests(unittest.TestCase):
        def setUp(self) -> None:
            self.app = None
            self.config = SuperDict(msg=False, timeLimit=1)

        @property
        def app(self) -> ApplicationCore:
            return self._app

        @app.setter
        def app(self, value) -> None:
            self._app = value

        def test_schema_load(self):
            self.assertIsInstance(self.app.instance.schema, dict)
            self.assertIsInstance(self.app.solution.schema, dict)
            self.assertIsInstance(self.app.schema, dict)
            self.assertIsInstance(self.app.instance.schema_checks, dict)

        def test_config_requirements(self):
            keys = {"solver", "timeLimit"}
            props = self.app.schema["properties"]
            dif = keys - props.keys()
            self.assertEqual(len(dif), 0)
            self.assertIn("enum", props["solver"])
            self.assertGreater(len(props["solver"]["enum"]), 0)

        def test_try_solving_testcase(self, config=None):
            config = config or self.config
            tests = self.app.test_cases

            for test_case in tests:
                instance_data = test_case.get("instance")
                solution_data = test_case.get("solution", None)
                case_name = test_case.get("name")
                case_description = test_case.get("description", "No description")

                marshm = SchemaManager(self.app.instance.schema).jsonschema_to_flask()
                marshm().load(instance_data)
                if solution_data is not None:
                    (
                        solution_test,
                        solution_check,
                        inst_check,
                        log,
                        log_dict,
                    ) = self.app.solve(instance_data, config, solution_data)
                else:
                    # for compatibility with previous format
                    (
                        solution_test,
                        solution_check,
                        inst_check,
                        log,
                        log_dict,
                    ) = self.app.solve(instance_data, config)
                if solution_test is None:
                    raise ValueError("No solution found")

                validator = Draft7Validator(self.app.solution.schema)
                if not validator.is_valid(solution_test):
                    raise Exception("The solution has invalid format")

                self.assertTrue(len(solution_test) > 0)
                instance = self.app.instance.from_dict(instance_data)
                solution = self.app.solution.from_dict(solution_test)
                s = self.app.get_default_solver_name()
                experiment = self.app.get_solver(s)(instance, solution)
                self.assertIsInstance(experiment.schema_checks, dict)
                checks = experiment.check_solution()
                failed_checks = [k for k, v in checks.items() if len(v) > 0]
                if len(failed_checks) > 0:
                    print(
                        f"Test instance {case_name} ({case_description}) "
                        f"failed with the following checks:"
                    )
                    for check, values in checks.items():
                        if len(values) > 0:
                            print(f"{check}: {values}")

                experiment.get_objective()

                validator = Draft7Validator(experiment.schema_checks)
                if not validator.is_valid(solution_check):
                    raise Exception("The solution checks have invalid format")

                validator = Draft7Validator(instance.schema_checks)

                if not validator.is_valid(inst_check):
                    raise Exception("The instance checks have invalid format")

        @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
        def test_complete_solve(self, connectCornflow, config=None):
            config = config or self.config
            tests = self.app.test_cases
            for test_case in tests:
                instance_data = test_case.get("instance")
                solution_data = test_case.get("solution", None)

                mock = Mock()
                mock.get_data.return_value = dict(
                    data=instance_data, config=config, id=1, solution_data=solution_data
                )
                connectCornflow.return_value = mock
                dag_run = Mock()
                dag_run.conf = dict(exec_id="exec_id")
                ti = Mock()
                ti.run_id = "run_id"
                ti.dag_id = "dag_id"
                ti.try_number = 1
                ti.task_id = "task_id"

                cf_solve(
                    fun=self.app.solve,
                    dag_name=self.app.name,
                    secrets="",
                    dag_run=dag_run,
                    ti=ti,
                    conf=dict(),
                )
                mock.get_data.assert_called_once()
                mock.write_solution.assert_called_once()


class GraphColorTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.graph_coloring import GraphColoring

        self.app = GraphColoring()
        self.config = dict(msg=False)


class TspTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.tsp import TspApp

        self.app = TspApp()

    def test_solve_cpsat(self):
        return self.test_try_solving_testcase(dict(solver="cpsat", **self.config))


class VrpTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.vrp import VRP

        self.app = VRP()

    def test_solve_ortools(self):
        return self.test_try_solving_testcase(dict(solver="algorithm3", **self.config))

    def test_solve_algorithm1(self):
        return self.test_try_solving_testcase(dict(solver="algorithm1", **self.config))

    def test_solve_heuristic(self):
        return self.test_try_solving_testcase(dict(solver="algorithm2", **self.config))

    def test_solve_mip(self):
        self.config.update(dict(solver="mip", timeLimit=2))
        return self.test_try_solving_testcase(self.config)


class KnapsackTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.knapsack import Knapsack

        self.app = Knapsack()

    def test_solve_dynamic(self):
        return self.test_try_solving_testcase(dict(solver="Dynamic", **self.config))

    def test_solve_random(self):
        return self.test_try_solving_testcase(dict(solver="Random", **self.config))

    def test_solve_other3(self):
        return self.test_try_solving_testcase(dict(solver="Direct", **self.config))

    def test_solve_mip(self):
        return self.test_try_solving_testcase(dict(solver="MIP.cbc", **self.config))


class RoadefTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.roadef import Roadef

        self.config.update({"timeLimit": 10, "seconds": 10})
        self.app = Roadef()

    def test_solve_mip(self):
        return self.test_try_solving_testcase(
            dict(solver="MIPModel.PULP_CBC_CMD", **self.config)
        )

    def test_solve_periodic_mip(self):
        return self.test_try_solving_testcase(
            dict(solver="PeriodicMIPModel.PULP_CBC_CMD", **self.config)
        )

    def test_read_xml(self):
        data_dir = os.path.join(os.path.dirname(__file__), "../../DAG/roadef/data/")
        instance = self.app.instance.from_file(
            data_dir + "Instance_V_1.0_ConvertedTo_V2.xml"
        )
        instance = self.app.instance.from_dict(instance.to_dict())
        self.assertEqual(instance.get_customer_property(2, "allowedTrailers"), [0, 1])
        self.assertEqual(len(instance.check_schema()), 0)


class BarCuttingTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.bar_cutting import BarCutting

        self.app = BarCutting()

    def test_solve_mip(self):
        return self.test_try_solving_testcase(dict(solver="mip.cbc", **self.config))

    def test_solve_column_generation(self):
        return self.test_try_solving_testcase(dict(solver="CG.cbc", **self.config))


class FacilityLocationTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.facility_location import FacilityLocation

        self.app = FacilityLocation()
        self.config.update(dict(solver="Pyomo.cbc", abs_gap=1, rel_gap=0.01))


class PuLPTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.solve_model_dag import PuLP

        self.app = PuLP()
        self.config.update(dict(solver="PULP_CBC_CMD"))


class TwoBinPackingTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.two_dimension_bin_packing import TwoDimensionBinPackingProblem

        self.app = TwoDimensionBinPackingProblem()
        self.config.update(dict(solver="right_corner.cbc"), timeLimit=10, msg=True)


class TimerTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.dag_timer import Timer

        self.app = Timer()
        self.config.update(dict(solver="default", seconds=10))
