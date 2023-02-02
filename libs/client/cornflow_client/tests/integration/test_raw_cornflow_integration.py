"""
Integration test for the Cornflow client
Base, admin and service user get tested
Integration between Airflow and cornflow through airflow client and cornflow client tested as well
"""
# Full imports
import json
import os
import pulp as pl
import time

# Partial imports
from unittest import TestCase

# Internal imports
from cornflow_client import CornFlow
from cornflow_client.constants import STATUS_OPTIMAL, STATUS_NOT_SOLVED, STATUS_QUEUED
from cornflow_client.schema.tools import get_pulp_jsonschema
from cornflow_client.tests.const import PUBLIC_DAGS, PULP_EXAMPLE

# Constants
path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))

# Helper functions
def _load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


# Testing suit classes
class TestRawCornflowClientUser(TestCase):
    def setUp(self):
        self.client = CornFlow(url="http://127.0.0.1:5050/")
        login_result = self.client.raw.login("user", "UserPassword1!")
        data = login_result.json()
        self.assertEqual(login_result.status_code, 200)
        self.assertIn("id", data.keys())
        self.assertIn("token", data.keys())
        self.user_id = data["id"]

    def tearDown(self):
        pass

    def test_health_endpoint(self):
        response = self.client.raw.is_alive()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["cornflow_status"], "healthy")
        self.assertEqual(data["airflow_status"], "healthy")

    def test_sign_up(self):
        response = self.client.raw.sign_up(
            "test_username_2", "test_username_2@cornflow.org", "TestPassword2!"
        )
        data = response.json()
        self.assertIn("id", data.keys())
        self.assertIn("token", data.keys())
        self.assertEqual(201, response.status_code)

    def test_create_instance(self):
        data = _load_file(PULP_EXAMPLE)
        response = self.client.raw.create_instance(data, "test_example", "test_description")
        self.assertEqual(response.status_code, 201)
        instance = response.json()

        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "executions",
        ]
        for item in items:
            self.assertIn(item, instance.keys())
        self.assertEqual("test_example", instance["name"])
        self.assertEqual("solve_model_dag", instance["schema"])
        self.assertEqual("test_description", instance["description"])

        return instance

    def test_create_case(self):
        data = _load_file(PULP_EXAMPLE)
        response = self.client.raw.create_case(
            name="test_case",
            schema="solve_model_dag",
            data=data,
            description="test_description",
        )
        self.assertEqual(response.status_code, 201)
        case = response.json()

        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "solution_hash",
            "path",
            "updated_at",
            "is_dir",
        ]

        for item in items:
            self.assertIn(item, case.keys())
        self.assertEqual("test_case", case["name"])
        self.assertEqual("solve_model_dag", case["schema"])
        self.assertEqual("test_description", case["description"])
        return case

    def test_create_instance_file(self):
        response = self.client.raw.create_instance_file(
            _get_file("../data/test_mps.mps"),
            name="test_filename",
            description="filename_description",
        )
        instance = response.json()
        self.assertEqual(response.status_code, 201)

        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "executions",
        ]

        for item in items:
            self.assertIn(item, instance.keys())
        self.assertEqual("test_filename", instance["name"])
        self.assertEqual("solve_model_dag", instance["schema"])
        self.assertEqual("filename_description", instance["description"])

    def test_create_execution(self):
        instance = self.test_create_instance()
        response = self.client.raw.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        )
        self.assertEqual(response.status_code, 201)
        execution = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "config",
            "instance_id",
            "state",
            "message",
        ]

        for item in items:
            self.assertIn(item, execution.keys())
        self.assertEqual(instance["id"], execution["instance_id"])
        self.assertEqual("test_execution", execution["name"])
        self.assertEqual("execution_description", execution["description"])
        self.assertEqual(
            {"solver": "PULP_CBC_CMD", "timeLimit": 60}, execution["config"]
        )
        self.assertEqual(STATUS_QUEUED, execution["state"])

        return execution

    def test_create_execution_data_check(self):
        exec_to_check = self.test_create_execution()
        time.sleep(15)
        exec_to_check_id = exec_to_check["id"]
        response = self.client.raw.create_execution_data_check(exec_to_check_id)
        execution = response.json()
        self.assertEqual(STATUS_QUEUED, execution["state"])
        return execution

    def test_execution_data_check_solution(self):
        execution = self.test_create_execution_data_check()
        time.sleep(15)
        results = self.client.raw.get_solution(execution["id"])
        self.assertEqual(results.status_code, 200)
        self.assertEqual(results.json()["state"], 1)

    def test_create_instance_data_check(self):
        inst_to_check = self.test_create_instance()
        inst_to_check_id = inst_to_check["id"]
        response = self.client.raw.create_instance_data_check(inst_to_check_id)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(STATUS_QUEUED, data["state"])
        config = data.get("config")
        self.assertIsInstance(config, dict)
        self.assertTrue(config.get("checks_only"))
        self.assertEqual(data.get("schema"), "solve_model_dag")
        self.assertEqual(data.get("instance_id"), inst_to_check_id)
        return data

    def test_instance_data_check_solution(self):
        execution = self.test_create_instance_data_check()
        time.sleep(15)
        results = self.client.raw.get_solution(execution["id"])
        self.assertEqual(results.status_code, 200)
        self.assertEqual(results.json()["state"], 1)
        response = self.client.raw.get_api_for_id(
            api="instance", id=execution["instance_id"], post_url="data", encoding="br"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["checks"])

    def test_execution_results(self):
        execution = self.test_create_execution()
        time.sleep(10)
        response = self.client.raw.get_results(execution["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()

        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "config",
            "instance_id",
            "state",
            "message",
        ]

        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(execution["id"], response["id"])
        self.assertEqual(STATUS_OPTIMAL, response["state"])

    def test_execution_status(self):
        execution = self.test_create_execution()
        self.assertEqual(STATUS_QUEUED, execution["state"])

        time.sleep(4)
        response = self.client.raw.get_status(execution["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = ["id", "state", "message", "data_hash"]
        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual(STATUS_NOT_SOLVED, response["state"])

        time.sleep(10)
        response = self.client.raw.get_status(execution["id"])
        self.assertEqual(response.status_code, 200)
        for item in items:
            self.assertIn(item, response.json().keys())
        self.assertEqual(STATUS_OPTIMAL, response.json()["state"])

    def test_stop_execution(self):
        execution = self.test_create_execution()
        response = self.client.raw.stop_execution(execution["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "The execution has been stopped")

    def test_get_execution_log(self):
        execution = self.test_create_execution()
        response = self.client.raw.get_log(execution["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "config",
            "instance_id",
            "state",
            "message",
            "log",
        ]

        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual(execution["id"], response["id"])

    def test_get_execution_solution(self):
        execution = self.test_create_execution()
        time.sleep(15)
        response = self.client.raw.get_solution(execution["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "config",
            "instance_id",
            "state",
            "message",
            "data",
            "checks",
        ]

        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(execution["id"], response["id"])
        self.assertEqual(STATUS_OPTIMAL, response["state"])

        return response

    def test_put_one_execution(self):
        execution = self.test_create_execution()
        response = self.client.raw.put_one_execution(execution["id"], {"name": "new_execution_name"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("Updated correctly", response.json()["message"])

    def test_delete_one_execution(self):
        execution = self.test_create_execution()
        response = self.client.raw.delete_one_execution(execution["id"])
        self.assertEqual(200, response.status_code)
        self.assertEqual("The object has been deleted", response.json()["message"])

    def test_create_case_execution(self):
        execution = self.test_get_execution_solution()
        response = self.client.raw.create_case(
            name="case_from_solution",
            schema="solve_model_dag",
            description="case_from_solution_description",
            solution=execution["data"],
        )
        self.assertEqual(response.status_code, 201)
        response = response.json()

        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "solution_hash",
            "path",
            "updated_at",
            "is_dir",
        ]

        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual("case_from_solution", response["name"])
        self.assertEqual("solve_model_dag", response["schema"])
        self.assertEqual("case_from_solution_description", response["description"])
        return response

    def test_get_all_instances(self):
        self.test_create_instance()
        self.test_create_instance()
        instances = self.client.raw.get_all_instances()
        self.assertEqual(instances.status_code, 200)
        self.assertGreaterEqual(len(instances.json()), 2)

    def test_get_all_executions(self):
        self.test_stop_execution()
        self.test_stop_execution()
        executions = self.client.raw.get_all_executions()
        self.assertEqual(executions.status_code, 200)
        self.assertGreaterEqual(len(executions.json()), 2)

    def test_get_all_cases(self):
        self.test_create_case()
        self.test_create_case()
        cases = self.client.raw.get_all_cases()
        self.assertEqual(cases.status_code, 200)
        self.assertGreaterEqual(len(cases.json()), 2)

    def test_get_one_user(self):
        response = self.client.raw.get_one_user(self.user_id)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = ["id", "first_name", "last_name", "username", "email"]
        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(self.user_id, response["id"])
        self.assertEqual("user", response["username"])
        self.assertEqual("user@cornflow.org", response["email"])

    def test_get_one_instance(self):
        instance = self.test_create_instance()
        response = self.client.raw.get_one_instance(instance["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "executions",
        ]

        for item in items:
            self.assertIn(item, response.keys())
            self.assertEqual(instance[item], response[item])

    def test_get_one_instance_data(self):
        instance = self.test_create_instance()
        response = self.client.raw.get_one_instance_data(instance["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema"
        ]

        self.assertIn("data", response.keys())
        for item in items:
            self.assertIn(item, response.keys())
            self.assertEqual(instance[item], response[item])

    def test_put_one_instance(self):
        instance = self.test_create_instance()
        response = self.client.raw.put_one_instance(instance["id"], {"name": "new_instance_name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual("Updated correctly", response.json()["message"])

    def test_get_one_case(self):
        case = self.test_create_case()
        response = self.client.raw.get_one_case(case["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "solution_hash",
            "path",
            "updated_at",
            "is_dir",
        ]

        for item in items:
            self.assertIn(item, response.keys())
            self.assertEqual(case[item], response[item])

    def test_get_one_case_data(self):
        case = self.test_create_case()
        response = self.client.raw.get_one_case_data(case["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "solution_hash",
            "path",
            "updated_at",
            "is_dir",
        ]

        self.assertIn("data", response.keys())
        for item in items:
            self.assertIn(item, response.keys())
            self.assertEqual(case[item], response[item])

    def test_get_one_case_execution(self):
        case = self.test_create_case_execution()
        response = self.client.raw.get_one_case(case["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = [
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "data_hash",
            "schema",
            "solution_hash",
            "path",
            "updated_at",
            "is_dir",
        ]

        for item in items:
            self.assertIn(item, response.keys())
            self.assertEqual(case[item], response[item])

    def test_delete_one_case(self):
        case = self.test_create_case()
        response = self.client.raw.delete_one_case(case["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual("The object has been deleted", response.json()["message"])

    def test_put_one_case(self):
        case = self.test_create_case()
        response = self.client.raw.put_one_case(case["id"], {"name": "new_case_name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual("Updated correctly", response.json()["message"])

    def test_patch_one_case(self):
        # TODO: Get example of data patch for the tests
        pass

    def test_delete_one_instance(self):
        instance = self.test_create_instance()
        response = self.client.raw.delete_one_instance(instance["id"])
        self.assertEqual(200, response.status_code)
        self.assertEqual("The object has been deleted", response.json()["message"])

    def test_get_schema(self):
        response = self.client.raw.get_schema("solve_model_dag")
        self.assertEqual(response.status_code, 200)
        response = response.json()
        schema = {
            "config": get_pulp_jsonschema("solver_config.json"),
            "instance": get_pulp_jsonschema(),
            "solution": get_pulp_jsonschema(),
        }

        schema["config"]["properties"]["solver"]["enum"] = pl.listSolvers()
        schema["config"]["properties"]["solver"]["default"] = "PULP_CBC_CMD"

        for (key, value) in schema.items():
            self.assertDictEqual(value, response[key])

    def test_get_all_schemas(self):
        response = self.client.raw.get_all_schemas()
        read_schemas = [dag for v in response.json() for (_, dag) in v.items()]

        for schema in PUBLIC_DAGS:
            self.assertIn(schema, read_schemas)


class TestRawCornflowClientAdmin(TestCase):
    def setUp(self):
        self.client = CornFlow(url="http://127.0.0.1:5050/")
        login_result = self.client.login("admin", "Adminpassword1!")
        self.assertIn("id", login_result.keys())
        self.assertIn("token", login_result.keys())
        self.base_user_id = CornFlow(url="http://127.0.0.1:5050/").login(
            "user", "UserPassword1!"
        )["id"]

    def tearDown(self):
        pass

    def test_get_all_users(self):
        response = self.client.raw.get_all_users()
        self.assertGreaterEqual(len(response.json()), 3)

    def test_get_one_user(self):
        response = self.client.raw.get_one_user(self.base_user_id)
        self.assertEqual(response.status_code, 200)

        items = ["id", "first_name", "last_name", "username", "email"]
        for item in items:
            self.assertIn(item, response.json().keys())

        self.assertEqual(self.base_user_id, response.json()["id"])
        self.assertEqual("user", response.json()["username"])
        self.assertEqual("user@cornflow.org", response.json()["email"])


class TestRawCornflowClientService(TestCase):
    def setUp(self):
        self.client = CornFlow(url="http://127.0.0.1:5050/")
        login_result = self.client.login("airflow", "Airflow_test_password1")
        self.assertIn("id", login_result.keys())
        self.assertIn("token", login_result.keys())

    def tearDown(self):
        pass

    def test_get_execution_data(self):
        client = CornFlow(url="http://127.0.0.1:5050/")
        _ = client.login("user", "UserPassword1!")
        data = _load_file(PULP_EXAMPLE)
        instance = client.raw.create_instance(data, "test_example", "test_description").json()
        execution = client.raw.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        ).json()
        response = self.client.raw.get_data(execution["id"])
        self.assertEqual(response.status_code, 200)
        response = response.json()
        items = ["id", "data", "config"]

        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(instance["id"], response["id"])
        self.assertEqual(data, response["data"])
        self.assertEqual(execution["config"], response["config"])

    def test_write_execution_solution(self):
        client = CornFlow(url="http://127.0.0.1:5050/")
        _ = client.login("user", "UserPassword1!")
        data = _load_file(PULP_EXAMPLE)
        instance = client.raw.create_instance(data, "test_example", "test_description").json()
        execution = client.raw.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        ).json()

        time.sleep(15)

        solution = client.raw.get_solution(execution["id"]).json()

        payload = dict(
            state=1, log_json={}, log_text="", solution_schema="solve_model_dag"
        )
        payload["data"] = solution["data"]

        response = self.client.raw.write_solution(execution["id"], **payload)
        self.assertEqual("results successfully saved", response.json()["message"])

    def test_get_deployed_dags(self):
        response = self.client.raw.get_deployed_dags()
        self.assertEqual(response.status_code, 200)
        response = response.json()

        items = ["id", "description"]
        for item in items:
            self.assertIn(item, response[0].keys())

        deployed_dags = [v["id"] for v in response]

        for dag in PUBLIC_DAGS:
            self.assertIn(dag, deployed_dags)

    def test_post_deployed_dag(self):

        response = self.client.raw.create_deployed_dag(
            name="test_dag_2", description="test_dag_2_description"
        )
        self.assertEqual(response.status_code, 201)
        response = response.json()

        items = ["id", "description"]

        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual("test_dag_2", response["id"])
        self.assertEqual("test_dag_2_description", response["description"])