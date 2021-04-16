import os, sys
prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
import unittest
from unittest.mock import patch, Mock

try:
    from DAG.update_all_schemas import get_all_apps
except ImportError:
    from update_all_schemas import get_all_apps
from cornflow_client import SchemaManager
from cornflow_client.airflow.dag_utilities import cf_solve


class DAGTests(unittest.TestCase):

    def setUp(self) -> None:
        self.apps = get_all_apps()

    def test_schema_load(self):
        for app in self.apps:
            with self.subTest(app=app.name):
                self.assertIsInstance(app.instance, dict)
                self.assertIsInstance(app.solution, dict)

    def test_try_solving_testcase(self):
        for app in self.apps:
            try:
                tests = app.test_cases()
            except:
                continue
            for pos, data in enumerate(tests):
                with self.subTest(app=app.name, test=pos):
                    marshm = SchemaManager(app.instance).jsonschema_to_flask()
                    marshm().load(data)
                    solution, log, log_dict = app.solve(data, {})
                    marshm = SchemaManager(app.solution).jsonschema_to_flask()
                    marshm().load(solution)
                    marshm().validate(solution)
                    self.assertTrue(len(solution) > 0)

    @patch("cornflow_client.airflow.dag_utilities.get_arg")
    @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
    def test_complete_solve(self, connectCornflow, getArg):
        for app in self.apps:
            try:
                tests = app.test_cases()
            except:
                continue
            for pos, data in enumerate(tests):
                with self.subTest(app=app.name, test=pos):
                    mock = Mock()
                    mock.get_data.return_value = dict(data=data, config={})
                    connectCornflow.return_value = mock
                    getArg.return_value = ""
                    cf_solve(fun=app.solve, dag_name=app.name, secrets="")
                    getArg.assert_called()
                    mock.get_data.assert_called_once()
                    mock.write_solution.assert_called_once()
