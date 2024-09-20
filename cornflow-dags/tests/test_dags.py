import os, sys

prev_dir = os.path.join(os.path.dirname(__file__), "../")
my_paths = [prev_dir, os.path.join(prev_dir, "DAG")]
for __my_path in my_paths:
    sys.path.insert(1, __my_path)

import unittest
from unittest.mock import patch, Mock, MagicMock
from html.parser import HTMLParser

# we mock everything that's airflow related:
mymodule = MagicMock()
sys.modules["airflow"] = mymodule
sys.modules["airflow.operators.python"] = mymodule
sys.modules["airflow.models"] = mymodule
sys.modules["airflow.secrets.environment_variables"] = mymodule

from cornflow_client import SchemaManager, ApplicationCore
from cornflow_client.airflow.dag_utilities import (
    cf_solve,
    cf_report,
    AirflowDagException,
)
from jsonschema import Draft7Validator
from pytups import SuperDict

from typing import Dict, List, Tuple, Optional


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

        def test_config_requirements(self):
            keys = {"solver", "timeLimit"}
            props = self.app.schema["properties"]
            dif = keys - props.keys()
            self.assertEqual(len(dif), 0)
            self.assertIn("enum", props["solver"])
            self.assertGreater(len(props["solver"]["enum"]), 0)

        def load_experiment_from_dataset(self, dataset):
            instance_data = dataset.get("instance")
            solution_data = dataset.get("solution", None)
            instance = self.app.instance.from_dict(instance_data)
            solution = self.app.solution.from_dict(solution_data)
            s = self.app.get_default_solver_name()
            return self.app.get_solver(s)(instance, solution)

        def generate_check_report(self, my_experim, things_to_look, verbose=False):

            report_path = my_experim.generate_report()
            # check the file is created.
            self.assertTrue(os.path.exists(report_path))

            parser = HTMLCheckTags(things_to_look, verbose)
            with open(report_path, "r") as f:
                content = f.read()

            try:
                os.remove(report_path)
            except FileNotFoundError:
                pass
            self.assertRaises(StopIteration, parser.feed, content)

        def test_try_solving_testcase(self, config=None):
            config = config or self.config
            tests = self.app.get_unittest_cases()

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
                marshm = SchemaManager(self.app.solution.schema).jsonschema_to_flask()
                validator = Draft7Validator(self.app.solution.schema)
                if not validator.is_valid(solution_test):
                    raise Exception("The solution has invalid format")

                self.assertTrue(len(solution_test) > 0)
                instance = self.app.instance.from_dict(instance_data)
                solution = self.app.solution.from_dict(solution_test)
                s = self.app.get_default_solver_name()
                experim = self.app.get_solver(s)(instance, solution)
                checks = experim.check_solution()
                failed_checks = [k for k, v in checks.items() if len(v) > 0]
                if len(failed_checks) > 0:
                    print(
                        f"Test instance {case_name} ({case_description}) "
                        f"failed with the following checks:"
                    )
                    for check, values in checks.items():
                        if len(values) > 0:
                            print(f"{check}: {values}")

                experim.get_objective()

                validator = Draft7Validator(experim.schema_checks)
                if not validator.is_valid(solution_check):
                    raise Exception("The solution checks have invalid format")

                validator = Draft7Validator(instance.schema_checks)
                if not validator.is_valid(inst_check):
                    raise Exception("The instance checks have invalid format")

        @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
        def test_complete_solve(self, connectCornflow, config=None):
            config = config or self.config
            tests = self.app.get_unittest_cases()
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


class GraphColor(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.graph_coloring import GraphColoring

        self.app = GraphColoring()
        self.config = dict(msg=False)

    def test_incomplete_solution(self):
        tests = self.app.get_unittest_cases()
        solution_data = dict(assignment=[dict(node=1, color=1), dict(node=3, color=1)])
        my_experim = self.app.solvers["default"](
            self.app.instance.from_dict(tests[0]["instance"]),
            self.app.solution.from_dict(solution_data),
        )
        checks = my_experim.check_solution()
        self.assertEqual(len(checks["missing"]), 2)
        self.assertEqual(len(checks["pairs"]), 1)

    def test_report(self):
        tests = self.app.get_unittest_cases()
        my_experim = self.load_experiment_from_dataset(tests[0])
        my_experim.solve(dict())
        things_to_look = dict(
            section=[
                ("id", "solution"),
                ("id", "instance-statistics"),
                ("id", "graph-coloring"),
            ]
        )
        self.generate_check_report(
            my_experim, things_to_look=things_to_look, verbose=False
        )


try:
    from DAG.wind_problem import WindEnergyBattery

    class WindProblem(BaseDAGTests.SolvingTests):
        def setUp(self):
            super().setUp()

            self.app = WindEnergyBattery()

        @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
        def test_complete_report(self, connectCornflow, config=None):
            config = config or self.config
            config = dict(**config, report=dict(name="report"))
            tests = self.app.get_unittest_cases()
            for test_case in tests:
                instance_data = test_case.get("instance")
                solution_data = test_case.get("solution", None)
                if solution_data is None:
                    solution_data = dict(solution_node_values=[])

                mock = Mock()
                mock.get_data.return_value = dict(
                    data=instance_data, solution_data=solution_data
                )
                mock.get_results.return_value = dict(config=config, state=1)
                mock.create_report.return_value = dict(id=1)
                connectCornflow.return_value = mock
                dag_run = Mock()
                dag_run.conf = dict(exec_id="exec_id")
                cf_report(app=self.app, secrets="", dag_run=dag_run)
                mock.create_report.assert_called_once()
                mock.put_one_report.assert_called_once()

except ImportError:
    pass


class Tsp(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.tsp import TspApp

        self.app = TspApp()

    def test_solve_cpsat(self):
        return self.test_try_solving_testcase(dict(solver="cpsat", **self.config))

    def test_report(self):
        tests = self.app.get_unittest_cases()
        my_experim = self.app.solvers["cpsat"](self.app.instance(tests[0]["instance"]))
        my_experim.solve(dict())

        # let's just check for an element inside the html that we know should exist
        # in this case a few 'section' tags with an attribute with a specific id
        things_to_look = dict(
            section=[
                ("id", "solution"),
                ("id", "instance-statistics"),
                ("id", "tsp"),
            ]
        )
        self.generate_check_report(my_experim, things_to_look)

    def test_report_error(self):
        tests = self.app.get_unittest_cases()
        my_experim = self.app.solvers["cpsat"](self.app.instance(tests[0]["instance"]))
        my_experim.solve(dict())
        my_fun = lambda: my_experim.generate_report(report_name="wrong_name")
        self.assertRaises(FileNotFoundError, my_fun)

    def test_export(self):
        tests = self.app.get_unittest_cases()
        my_file_path = "export.json"
        self.app.instance(tests[0]["instance"]).to_json(my_file_path)
        self.assertTrue(os.path.exists(my_file_path))
        try:
            os.remove(my_file_path)
        except FileNotFoundError:
            pass

    @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
    def test_complete_report(self, connectCornflow, config=None):
        config = config or self.config
        config = dict(**config, report=dict(name="report"))
        tests = self.app.get_unittest_cases()
        for test_case in tests:
            instance_data = test_case.get("instance")
            solution_data = test_case.get("solution", None)
            if solution_data is None:
                solution_data = dict(route=[])

            mock = Mock()
            mock.get_data.return_value = dict(
                data=instance_data, solution_data=solution_data
            )
            mock.get_results.return_value = dict(config=config, state=1)
            mock.create_report.return_value = dict(id=1)
            connectCornflow.return_value = mock
            dag_run = Mock()
            dag_run.conf = dict(exec_id="exec_id")
            cf_report(app=self.app, secrets="", dag_run=dag_run)
            mock.create_report.assert_called_once()
            mock.put_one_report.assert_called_once()

    @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
    def test_complete_report_wrong_data(self, connectCornflow, config=None):
        config = config or self.config
        config = dict(**config, report=dict(name="report"))
        tests = self.app.get_unittest_cases()
        for test_case in tests:
            instance_data = test_case.get("instance")
            solution_data = None

            mock = Mock()
            mock.get_data.return_value = dict(
                data=instance_data, solution_data=solution_data
            )
            mock.get_results.return_value = dict(config=config, state=1)
            mock.create_report.return_value = dict(id=1)
            connectCornflow.return_value = mock
            dag_run = Mock()
            dag_run.conf = dict(exec_id="exec_id")
            my_report = lambda: cf_report(app=self.app, secrets="", dag_run=dag_run)
            self.assertRaises(AirflowDagException, my_report)
            mock.create_report.assert_called_once()
            mock.raw.put_api_for_id.assert_called_once()
            args, kwargs = mock.raw.put_api_for_id.call_args
            self.assertEqual(kwargs["data"], {"state": -1})

    @patch("quarto.render")
    @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
    def test_complete_report_no_quarto(self, connectCornflow, render, config=None):
        config = config or self.config
        config = dict(**config, report=dict(name="report"))
        tests = self.app.get_unittest_cases()
        render.side_effect = ModuleNotFoundError()
        render.return_value = dict(a=1)
        for test_case in tests:
            instance_data = test_case.get("instance")
            solution_data = test_case.get("solution", None)
            if solution_data is None:
                solution_data = dict(route=[])

            mock = Mock()
            mock.get_data.return_value = dict(
                data=instance_data,
                solution_data=solution_data,
            )
            mock.get_results.return_value = dict(config=config, state=1)
            mock.create_report.return_value = dict(id=1)
            connectCornflow.return_value = mock
            dag_run = Mock()
            dag_run.conf = dict(exec_id="exec_id")
            my_report = lambda: cf_report(app=self.app, secrets="", dag_run=dag_run)
            self.assertRaises(AirflowDagException, my_report)
            mock.create_report.assert_called_once()
            mock.raw.put_api_for_id.assert_called_once()
            args, kwargs = mock.raw.put_api_for_id.call_args
            self.assertEqual(kwargs["data"], {"state": -10})


class Vrp(BaseDAGTests.SolvingTests):
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


class Knapsack(BaseDAGTests.SolvingTests):
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


class Roadef(BaseDAGTests.SolvingTests):
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
        data_dir = os.path.join(os.path.dirname(__file__), "../DAG/roadef/data/")
        instance = self.app.instance.from_file(
            data_dir + "Instance_V_1.0_ConvertedTo_V2.xml"
        )
        instance = self.app.instance.from_dict(instance.to_dict())
        self.assertEqual(instance.get_customer_property(2, "allowedTrailers"), [0, 1])
        self.assertEqual(len(instance.check_schema()), 0)


class Rostering(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.rostering import Rostering

        self.app = Rostering()
        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))


class BarCutting(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.bar_cutting import BarCutting

        self.app = BarCutting()

    def test_solve_mip(self):
        return self.test_try_solving_testcase(dict(solver="mip.cbc", **self.config))

    def test_solve_column_generation(self):
        return self.test_try_solving_testcase(dict(solver="CG.cbc", **self.config))


class FacilityLocation(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.facility_location import FacilityLocation

        self.app = FacilityLocation()
        self.config.update(dict(solver="Pyomo.cbc", abs_gap=1, rel_gap=0.01))


class PuLP(BaseDAGTests.SolvingTests):
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
        self.config.update(dict(solver="right_corner.cbc"))


class Timer(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.dag_timer import Timer

        self.app = Timer()
        self.config.update(dict(solver="default", seconds=10))

    def test_report(self):
        my_experim = self.app.solvers["default"](self.app.instance({}))
        things_to_look = dict(div=[("class", "foo")], span=[("class", "bar")])
        self.generate_check_report(
            my_experim, things_to_look=things_to_look, verbose=False
        )


class Sudoku(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.sudoku import Sudoku

        self.app = Sudoku()

    def test_report(self):
        tests = self.app.get_unittest_cases()
        my_experim = self.app.solvers["cpsat"](self.app.instance(tests[0]["instance"]))
        my_experim.solve(dict())

        # let's just check for an element inside the html that we know should exist
        # in this case a few 'section' tags with an attribute with a specific id
        things_to_look = dict(
            section=[
                ("id", "solution"),
                ("id", "instance"),
                ("id", "sudoku"),
            ]
        )
        self.generate_check_report(my_experim, things_to_look)

    def test_two_solutions(self):
        my_instance = self.app.instance.from_txt_file(
            filePath=None,
            contents="..........12.34567.345.6182..1.582.6..86....1.2...7.5...37.5.28.8..6.7..2.7..3615",
        )
        my_experim = self.app.solvers["cpsat"](my_instance)
        my_experim.solve(dict())
        my_experim.solution.check_schema()
        indicators = my_experim.solution.get_indicators()
        self.assertFalse("num_fails" in indicators)
        others = my_experim.solution.get_others(my_experim.instance.get_size())
        required_keys = ["pos", "square", "id", "col", "row", "value"]
        self.assertTrue(
            len(others[0].keys_tl().intersect(required_keys)) == len(required_keys)
        )

    def test_easy_norvig(self):
        dataset = [
            t for t in self.app.get_unittest_cases() if t["name"].startswith("hardest")
        ][0]
        # we try solving in the standard way:
        self.app.solve(dataset["instance"], dict(solver="norvig"))

        # we solve it in more detail
        my_experim = self.app.solvers["norvig"](
            self.app.instance.from_dict(dataset["instance"])
        )
        my_experim.solve(dict())
        my_experim.solution.check_schema()
        indicators = my_experim.solution.get_indicators()
        self.assertTrue("num_fails" in indicators)
        others = my_experim.solution.get_others(my_experim.instance.get_size())
        self.assertTrue(len(others) == 0)

    def test_print(self):
        my_instance = self.app.instance.from_txt_file(
            filePath=None,
            contents="..........12.34567.345.6182..1.582.6..86....1.2...7.5...37.5.28.8..6.7..2.7..3615",
        )
        my_experim = self.app.solvers["cpsat"](my_instance)
        my_experim.solve(dict())
        my_ids = my_experim.get_others().take("id").unique()
        for _id in my_ids:
            my_experim.print(_id)

    def test_plot(self):
        my_instance = self.app.instance.from_txt_file(
            filePath=None,
            contents="..........12.34567.345.6182..1.582.6..86....1.2...7.5...37.5.28.8..6.7..2.7..3615",
        )
        my_experim = self.app.solvers["cpsat"](my_instance)
        my_experim.solve(dict())
        my_experim.plot()

    def test_report2(self):
        my_instance = self.app.instance.from_txt_file(
            filePath=None,
            contents="..........12.34567.345.6182..1.582.6..86....1.2...7.5...37.5.28.8..6.7..2.7..3615",
        )
        my_experim = self.app.solvers["cpsat"](my_instance)
        my_experim.solve(dict())

        # let's just check for an element inside the html that we know should exist
        # in this case a few 'section' tags with an attribute with a specific id
        things_to_look = dict(
            section=[
                ("id", "solution"),
                ("id", "instance"),
                ("id", "sudoku"),
            ]
        )
        self.generate_check_report(my_experim, things_to_look)

    def test_report3(self):
        dataset = [
            t for t in self.app.get_unittest_cases() if t["name"].startswith("hardest")
        ][0]
        # we try solving in the standard way:
        self.app.solve(dataset["instance"], dict(solver="norvig"))

        # we solve it in more detail
        my_experim = self.app.solvers["norvig"](
            self.app.instance.from_dict(dataset["instance"])
        )
        my_experim.solve(dict())

        # let's just check for an element inside the html that we know should exist
        # in this case a few 'section' tags with an attribute with a specific id
        things_to_look = dict(
            section=[
                ("id", "solution"),
                ("id", "instance"),
                ("id", "sudoku"),
            ]
        )
        self.generate_check_report(my_experim, things_to_look)


class HTMLCheckTags(HTMLParser):
    things_to_check: Optional[Dict[str, List[Tuple[str, str]]]]

    def __init__(self, things_to_check: Dict[str, List[Tuple[str, str]]], verbose):
        HTMLParser.__init__(self)
        self.verbose = verbose
        if things_to_check is None:
            self.things_to_check = None
        else:
            self.things_to_check = SuperDict(things_to_check).copy_deep()

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]):
        # when things_to_check is None, we traverse everything
        # when verbose=True, we print what we traverse
        if self.verbose:
            print("Start tag:", tag)
        if self.things_to_check is not None and tag not in self.things_to_check:
            return
        for attr in attrs:
            if self.verbose:
                print("     attr:", attr)
            # is we're not looking for keys, we just continue
            if self.things_to_check is None:
                continue
            try:
                # we find the element in the list and remove it
                index = self.things_to_check[tag].index(attr)
                self.things_to_check[tag].pop(index)
            except ValueError:
                continue
            # if the list is empty, we take out the key
            if not len(self.things_to_check[tag]):
                self.things_to_check.pop(tag)
                # if we have nothing else to check,
                # we stop searching
                if not (self.things_to_check):
                    raise StopIteration
