import os, sys

prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
import unittest
from unittest.mock import patch, Mock, MagicMock

# we mock everything that's airflow related:
mymodule = MagicMock()
sys.modules["airflow"] = mymodule
sys.modules["airflow.operators.python"] = mymodule
sys.modules["airflow.models"] = mymodule
sys.modules["airflow.secrets.environment_variables"] = mymodule

try:
    from DAG.update_all_schemas import _import_file
except ImportError:
    from update_all_schemas import _import_file
from cornflow_client import SchemaManager
from cornflow_client.airflow.dag_utilities import cf_solve


class BaseDAGTests:
    class SolvingTests(unittest.TestCase):
        def setUp(self) -> None:
            self.app = None
            self.config = {}

        def test_schema_load(self):
            self.assertIsInstance(self.app.instance, dict)
            self.assertIsInstance(self.app.solution, dict)

        def test_try_solving_testcase(self, config=None):
            config = config or self.config
            try:
                tests = self.app.test_cases()
            except:
                return
            for pos, data in enumerate(tests):
                marshm = SchemaManager(self.app.instance).jsonschema_to_flask()
                marshm().load(data)
                solution, log, log_dict = self.app.solve(data, config)
                marshm = SchemaManager(self.app.solution).jsonschema_to_flask()
                marshm().load(solution)
                marshm().validate(solution)
                self.assertTrue(len(solution) > 0)

        @patch("cornflow_client.airflow.dag_utilities.get_arg")
        @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
        def test_complete_solve(self, connectCornflow, getArg, config=None):
            config = config or self.config
            try:
                tests = self.app.test_cases()
            except:
                return
            for pos, data in enumerate(tests):
                mock = Mock()
                mock.get_data.return_value = dict(data=data, config=config)
                connectCornflow.return_value = mock
                getArg.return_value = ""
                cf_solve(fun=self.app.solve, dag_name=self.app.name, secrets="")
                getArg.assert_called()
                mock.get_data.assert_called_once()
                mock.write_solution.assert_called_once()


class Hackathon(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        self.app = _import_file("hk_2020_dag")

    def test_solve_ortools(self):
        return self.test_try_solving_testcase(dict(solver="ortools"))


class GraphColor(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        self.app = _import_file("graph_coloring")


class Knapsack(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        self.app = _import_file("knapsack")

    def test_solve_dynamic(self):
        return self.test_try_solving_testcase(dict(solver="Dynamic"))

    def test_solve_random(self):
        return self.test_try_solving_testcase(dict(solver="Random"))

    def test_solve_other3(self):
        return self.test_try_solving_testcase(dict(solver="algorithm3"))


class PuLP(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        self.app = _import_file("optim_dag")
