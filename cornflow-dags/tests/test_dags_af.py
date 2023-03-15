import json
import unittest
import os, sys, time

from cornflow_client.airflow.api import Airflow

prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
from DAG.update_all_schemas import get_new_apps, get_all_schemas, get_all_example_data
from DAG.auto_scripts.automatic_scripts import execute_scripts

ALL_VARIABLES = [k for k in get_all_schemas().keys()] + [
    k for k in get_all_example_data().keys()
]

EXISTING_APPS = [app.name for app in get_new_apps()]


class DAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.apps = get_new_apps()
        pass

    def run_update_all_variables_until_finished(self):
        client = Airflow(url="http://localhost:8080", user="admin", pwd="admin")
        response = client.consume_dag_run(dag_name="update_all_schemas", payload={})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        finished = False
        while not finished:
            time.sleep(2)
            status = client.get_dag_run_status("update_all_schemas", data["dag_run_id"])
            state = status.json()["state"]
            finished = state != "running"
            print("STATUS OF update_all_variables: {}".format(state))
        return client

    def test_all_dags_exist(self):
        names = [app.name for app in self.apps]
        missing = set(EXISTING_APPS).difference(names)
        print("Missing apps: {}".format(missing))
        self.assertEqual(len(missing), 0)

    def test_access_schemas(self):
        client = self.run_update_all_variables_until_finished()
        url = f"{client.url}/variables"
        response = client.request_headers_auth(method="GET", url=url)
        apps_variables = [k["key"] for k in response.json()["variables"]]
        print(f"The following apps have variables: {apps_variables}")
        for app in EXISTING_APPS:
            value = client.get_one_variable(app)
            content = json.loads(value["value"])
            self.assertIn("instance", content)
            self.assertIn("solution", content)
            self.assertIn("config", content)

    def test_access_all_variables(self):
        client = self.run_update_all_variables_until_finished()
        apps = [app["name"] for app in client.get_all_schemas()]
        self.assertEqual(apps, ALL_VARIABLES)

    def test_auto_scripts(self):
        script_folder = os.path.join(os.path.dirname(__file__), "./data/auto_scripts/")
        destination_folder = script_folder
        results = execute_scripts(script_folder, destination_folder)
        self.assertEqual(results, 200)
