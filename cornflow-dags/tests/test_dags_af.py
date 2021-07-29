import json
import unittest
from cornflow_client.airflow.api import Airflow

import os, sys

prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
try:
    from DAG.update_all_schemas import update_schemas, get_all_apps
except ImportError:
    from update_all_schemas import update_schemas, get_all_apps


existing_apps = [
    "timer",
    "solve_model_dag",
    "graph_coloring",
    "hk_2020_dag",
    "knapsack",
    "vrp",
]


class DAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.apps = get_all_apps()
        pass

    def test_all_dags_exist(self):
        names = [app.name for app in self.apps]
        missing = set(existing_apps).difference(names)
        self.assertEqual(len(missing), 0)

    def test_access_variables(self):
        client = Airflow(url="http://localhost:8080", user="admin", pwd="admin")
        response = client.consume_dag_run(dag_name="update_all_schemas", payload={})
        self.assertEqual(response.status_code, 200)
        for app in existing_apps:
            value = client.get_one_variable(app)
            content = json.loads(value)
            self.assertIn("instance", content)
            self.assertIn("solution", content)
            self.assertIn("config", content)
