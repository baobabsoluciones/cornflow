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
class TestCornflowClientUser(TestCase):
    def setUp(self):
        self.client = CornFlow(url="http://127.0.0.1:5050/")
        login_result = self.client.login("user", "UserPassword1!")
        self.assertIn("id", login_result.keys())
        self.assertIn("token", login_result.keys())
        self.user_id = login_result["id"]

    def tearDown(self):
        pass

    def test_health_endpoint(self):
        response = self.client.is_alive()
        self.assertEqual(response["cornflow_status"], "healthy")
        self.assertEqual(response["airflow_status"], "healthy")

    def test_sign_up(self):
        response = self.client.sign_up(
            "test_username", "test_username@cornflow.org", "TestPassword2!"
        )
        self.assertIn("id", response.keys())
        self.assertIn("token", response.keys())

    def test_create_instance(self):
        data = _load_file(PULP_EXAMPLE)
        response = self.client.create_instance(data, "test_example", "test_description")
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

        self.assertEqual("test_example", response["name"])
        self.assertEqual("solve_model_dag", response["schema"])
        self.assertEqual("test_description", response["description"])

        return response

    def test_create_case(self):
        data = _load_file(PULP_EXAMPLE)
        response = self.client.create_case(
            name="test_case",
            schema="solve_model_dag",
            data=data,
            description="test_description",
        )

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
        self.assertEqual("test_case", response["name"])
        self.assertEqual("solve_model_dag", response["schema"])
        self.assertEqual("test_description", response["description"])
        return response

    def test_create_instance_file(self):
        response = self.client.create_instance_file(
            _get_file("../data/test_mps.mps"),
            name="test_filename",
            description="filename_description",
        )

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

        self.assertEqual("test_filename", response["name"])
        self.assertEqual("solve_model_dag", response["schema"])
        self.assertEqual("filename_description", response["description"])

    def test_create_execution(self):
        instance = self.test_create_instance()
        response = self.client.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        )
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

        self.assertEqual(instance["id"], response["instance_id"])
        self.assertEqual("test_execution", response["name"])
        self.assertEqual("execution_description", response["description"])
        self.assertEqual(
            {"solver": "PULP_CBC_CMD", "timeLimit": 60}, response["config"]
        )
        self.assertEqual(STATUS_QUEUED, response["state"])

        return response

    def test_create_execution_data_check(self):
        exec_to_check = self.test_create_execution()
        time.sleep(15)
        exec_to_check_id = exec_to_check["id"]
        execution = self.client.create_execution_data_check(exec_to_check_id)
        self.assertEqual(STATUS_QUEUED, execution["state"])
        return execution

    def test_execution_data_check_solution(self):
        execution = self.test_create_execution_data_check()
        time.sleep(15)
        results = self.client.get_solution(execution["id"])
        self.assertEqual(results["state"], 1)

    def test_create_instance_data_check(self):
        inst_to_check = self.test_create_instance()
        inst_to_check_id = inst_to_check["id"]
        execution = self.client.create_instance_data_check(inst_to_check_id)
        self.assertEqual(STATUS_QUEUED, execution["state"])
        config = execution.get("config")
        self.assertIsInstance(config, dict)
        self.assertTrue(config.get("checks_only"))
        self.assertEqual(execution.get("schema"), "solve_model_dag")
        self.assertEqual(execution.get("instance_id"), inst_to_check_id)
        return execution

    def test_instance_data_check_solution(self):
        execution = self.test_create_instance_data_check()
        time.sleep(15)
        results = self.client.get_solution(execution["id"])
        self.assertEqual(results["state"], 1)
        response = self.client.get_one_instance_data(
            reference_id=execution["instance_id"], encoding="br"
        )
        self.assertIsNotNone(response["checks"])

    def test_execution_results(self):
        execution = self.test_create_execution()
        time.sleep(10)
        response = self.client.get_results(execution["id"])

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
        response = self.client.get_status(execution["id"])
        items = ["id", "state", "message", "data_hash"]
        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual(STATUS_NOT_SOLVED, response["state"])

        time.sleep(10)
        response = self.client.get_status(execution["id"])
        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual(STATUS_OPTIMAL, response["state"])

    def test_stop_execution(self):
        execution = self.test_create_execution()
        response = self.client.stop_execution(execution["id"])
        self.assertEqual(response["message"], "The execution has been stopped")

    def test_get_execution_log(self):
        execution = self.test_create_execution()
        response = self.client.get_log(execution["id"])

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
        response = self.client.get_solution(execution["id"])
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
        response = self.client.put_one_execution(execution["id"], {"name": "new_execution_name"})
        self.assertEqual("Updated correctly", response["message"])

    def test_delete_one_execution(self):
        execution = self.test_create_execution()
        response = self.client.delete_one_execution(execution["id"])
        self.assertEqual("The object has been deleted", response["message"])

    def test_create_case_execution(self):
        execution = self.test_get_execution_solution()
        response = self.client.create_case(
            name="case_from_solution",
            schema="solve_model_dag",
            description="case_from_solution_description",
            solution=execution["data"],
        )

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
        instances = self.client.get_all_instances()
        self.assertGreaterEqual(len(instances), 2)

    def test_get_all_executions(self):
        self.test_stop_execution()
        self.test_stop_execution()
        executions = self.client.get_all_executions()
        self.assertGreaterEqual(len(executions), 2)

    def test_get_all_cases(self):
        self.test_create_case()
        self.test_create_case()
        cases = self.client.get_all_cases()
        self.assertGreaterEqual(len(cases), 2)

    def test_get_one_user(self):
        response = self.client.get_one_user(self.user_id)

        items = ["id", "first_name", "last_name", "username", "email"]
        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(self.user_id, response["id"])
        self.assertEqual("user", response["username"])
        self.assertEqual("user@cornflow.org", response["email"])

    def test_get_one_instance(self):
        instance = self.test_create_instance()
        response = self.client.get_one_instance(instance["id"])
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
        response = self.client.get_one_instance_data(instance["id"])
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
        response = self.client.put_one_instance(instance["id"], {"name": "new_instance_name"})
        self.assertEqual("Updated correctly", response["message"])

    def test_get_one_case(self):
        case = self.test_create_case()
        response = self.client.get_one_case(case["id"])
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
        response = self.client.get_one_case_data(case["id"])
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
        response = self.client.get_one_case(case["id"])
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
        response = self.client.delete_one_case(case["id"])
        self.assertEqual("The object has been deleted", response["message"])

    def test_put_one_case(self):
        case = self.test_create_case()
        response = self.client.put_one_case(case["id"], {"name": "new_case_name"})
        self.assertEqual("Updated correctly", response["message"])

    def test_patch_one_case(self):
        # TODO: Get example of data patch for the tests
        pass

    def test_delete_one_instance(self):
        instance = self.test_create_instance()
        response = self.client.delete_one_instance(instance["id"])
        self.assertEqual("The object has been deleted", response["message"])

    def test_get_schema(self):
        response = self.client.get_schema("solve_model_dag")
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
        response = self.client.get_all_schemas()
        read_schemas = [dag for v in response for (_, dag) in v.items()]

        for schema in PUBLIC_DAGS:
            self.assertIn(schema, read_schemas)


class TestCornflowClientAdmin(TestCase):
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
        response = self.client.get_all_users()
        self.assertGreaterEqual(len(response), 3)

    def test_get_one_user(self):
        response = self.client.get_one_user(self.base_user_id)

        items = ["id", "first_name", "last_name", "username", "email"]
        for item in items:
            self.assertIn(item, response.keys())

        self.assertEqual(self.base_user_id, response["id"])
        self.assertEqual("user", response["username"])
        self.assertEqual("user@cornflow.org", response["email"])


class TestCornflowClientService(TestCase):
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
        instance = client.create_instance(data, "test_example", "test_description")
        execution = client.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        )
        response = self.client.get_data(execution["id"])
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
        instance = client.create_instance(data, "test_example", "test_description")
        execution = client.create_execution(
            instance_id=instance["id"],
            config={"solver": "PULP_CBC_CMD", "timeLimit": 60},
            name="test_execution",
            description="execution_description",
            schema="solve_model_dag",
        )

        time.sleep(15)

        solution = client.get_solution(execution["id"])

        payload = dict(
            state=1, log_json={}, log_text="", solution_schema="solve_model_dag"
        )
        payload["data"] = solution["data"]

        response = self.client.write_solution(execution["id"], **payload)
        self.assertEqual("results successfully saved", response["message"])

    def test_get_deployed_dags(self):
        response = self.client.get_deployed_dags()

        items = ["id", "description"]
        for item in items:
            self.assertIn(item, response[0].keys())

        deployed_dags = [v["id"] for v in response]

        for dag in PUBLIC_DAGS:
            self.assertIn(dag, deployed_dags)

    def test_post_deployed_dag(self):

        response = self.client.create_deployed_dag(
            name="test_dag", description="test_dag_description"
        )

        items = ["id", "description"]

        for item in items:
            self.assertIn(item, response.keys())
        self.assertEqual("test_dag", response["id"])
        self.assertEqual("test_dag_description", response["description"])
