import json
import unittest
import os, sys, time

from cornflow_client.airflow.api import Airflow

prev_dir = os.path.join(os.path.dirname(__file__), "../DAG")
sys.path.insert(1, prev_dir)
from DAG.update_all_schemas import get_new_apps

existing_apps = [app.name for app in get_new_apps()]


class DAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.apps = get_new_apps()
        pass

    def test_all_dags_exist(self):
        names = [app.name for app in self.apps]
        missing = set(existing_apps).difference(names)
        print("Missing apps: {}".format(missing))
        self.assertEqual(len(missing), 0)

    def run_update_all_schemas_until_finished(self):
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
            print("STATUS OF update_all_schemas: {}".format(state))
        return client

    def test_access_variables(self):
        client = self.run_update_all_schemas_until_finished()
        url = "{}/variables".format(client.url)
        response = client.request_headers_auth(method="GET", url=url)
        print(
            "The following apps have variables: {}".format(
                [k["key"] for k in response.json()["variables"]]
            )
        )
        for app in existing_apps:
            value = client.get_one_variable(app)
            content = json.loads(value["value"])
            self.assertIn("instance", content)
            self.assertIn("solution", content)
            self.assertIn("config", content)

    def test_access_all_variables(self):
        client = self.run_update_all_schemas_until_finished()
        apps = [app["name"] for app in client.get_all_schemas()]
        self.assertEqual(apps, existing_apps)
