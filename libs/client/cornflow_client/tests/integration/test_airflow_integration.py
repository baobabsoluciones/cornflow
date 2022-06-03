"""

"""
import json
import os
import time
from unittest import TestCase

from cornflow_client import CornFlow
from cornflow_client.airflow.api import Airflow
from cornflow_client.constants import STATUS_OPTIMAL, STATUS_NOT_SOLVED
from cornflow_client.tests.const import PULP_EXAMPLE

# Constants
path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))

# Helper functions
def _load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


class TestAirflowClient(TestCase):
    def setUp(self):
        self.client = Airflow(url="http://127.0.0.1:8080", user="admin", pwd="admin")

    def test_alive(self):
        self.assertTrue(self.client.is_alive())

    def test_connect_from_config(self):
        client = Airflow.from_config(
            {
                "AIRFLOW_URL": "http://127.0.0.1:8080",
                "AIRFLOW_USER": "admin",
                "AIRFLOW_PWD": "admin",
            }
        )
        self.assertTrue(client.is_alive())

    def test_bad_connection(self):
        client = Airflow(url="http://127.0.0.1:8088", user="admin", pwd="admin!")
        self.assertFalse(client.is_alive())

    def test_update_schemas(self):
        response = self.client.update_schemas()
        self.assertEqual(200, response.status_code)

    def test_update_dag_registry(self):
        response = self.client.update_dag_registry()
        self.assertEqual(200, response.status_code)

    def test_run_dag(self):
        data = _load_file(PULP_EXAMPLE)
        cf_client = CornFlow(url="http://127.0.0.1:5050/")
        cf_login = cf_client.login("user", "UserPassword1!")
        instance = cf_client.create_instance(data, "test_example", "test_description")
        execution = cf_client.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 100},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
            run=False,
        )

        # Check that execution is not run
        status = cf_client.get_status(execution_id=execution["id"])
        self.assertEqual(-4, status["state"])

        # Run the execution
        response = self.client.run_dag(execution_id=execution["id"])
        self.assertEqual(200, response.status_code)
        self.assertIn("dag_run_id", response.json().keys())

        # Check that is optimal
        time.sleep(10)
        status = cf_client.get_status(execution_id=execution["id"])
        self.assertEqual(1, status["state"])
