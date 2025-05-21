"""
Unit test for the executions endpoints
"""

# Import from libraries
import json
from unittest.mock import patch

# Import from internal modules
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.const import (
    INSTANCE_PATH,
    EXECUTION_PATH,
    EXECUTIONS_LIST,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_URL,
    DAG_URL,
    BAD_EXECUTION_PATH,
    EXECUTION_SOLUTION_PATH,
    CUSTOM_CONFIG_PATH,
)
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
from cornflow.tests.unit.tools import patch_af_client


class TestExecutionsListEndpoint(BaseTestCases.ListFilters):
    def setUp(self):
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.url = EXECUTION_URL_NORUN
        self.model = ExecutionModel

        def load_file_fk(_file):
            with open(_file) as f:
                temp = json.load(f)
            temp["instance_id"] = fk_id
            return temp

        self.payload = load_file_fk(EXECUTION_PATH)
        self.bad_payload = load_file_fk(BAD_EXECUTION_PATH)
        self.payloads = [load_file_fk(f) for f in EXECUTIONS_LIST]
        self.solution = load_file_fk(EXECUTION_SOLUTION_PATH)
        self.custom_config_payload = load_file_fk(CUSTOM_CONFIG_PATH)
        self.keys_to_check = [
            "data_hash",
            "created_at",
            "config",
            "state",
            "message",
            "schema",
            "description",
            "id",
            "user_id",
            "log",
            "instance_id",
            "name",
            "indicators",
            "username",
            "updated_at"
        ]

    def test_new_execution(self):
        self.create_new_row(self.url, self.model, payload=self.payload)

    def test_get_custom_config(self):
        id = self.create_new_row(
            self.url, self.model, payload=self.custom_config_payload
        )
        url = EXECUTION_URL + "/" + str(id) + "/" + "?run=0"

        response = self.get_one_row(
            url,
            payload={**self.custom_config_payload, **dict(id=id)},
        )
        self.assertEqual(response["config"]["block_model"]["solver"], "mip.gurobi")

    @patch("cornflow.endpoints.execution.Airflow")
    def test_new_execution_run(self, af_client_class):
        patch_af_client(af_client_class)

        self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)

    @patch("cornflow.endpoints.execution.Airflow")
    def test_new_execution_bad_config(self, af_client_class):
        patch_af_client(af_client_class)
        response = self.create_new_row(
            EXECUTION_URL,
            self.model,
            payload=self.bad_payload,
            expected_status=400,
            check_payload=False,
        )
        self.assertIn("error", response)
        self.assertIn("jsonschema_errors", response)

    @patch("cornflow.endpoints.execution.Airflow")
    def test_new_execution_partial_config(self, af_client_class):
        patch_af_client(af_client_class)
        self.payload["config"].pop("solver")
        response = self.create_new_row(
            EXECUTION_URL, self.model, payload=self.payload, check_payload=False
        )
        self.assertIn("solver", response["config"])
        self.assertEqual(response["config"]["solver"], "cbc")

    @patch("cornflow.endpoints.execution.Airflow")
    def test_new_execution_with_solution(self, af_client_class):
        patch_af_client(af_client_class)
        self.payload["data"] = self.solution
        response = self.create_new_row(
            EXECUTION_URL,
            self.model,
            payload=self.payload,
            check_payload=False,
        )

    @patch("cornflow.endpoints.execution.Airflow")
    def test_new_execution_with_solution_bad(self, af_client_class):
        patch_af_client(af_client_class)
        patch_af_client(af_client_class)
        self.payload["data"] = {"message": "THIS IS NOT A VALID SOLUTION"}
        response = self.create_new_row(
            EXECUTION_URL,
            self.model,
            payload=self.payload,
            check_payload=False,
            expected_status=400,
        )
        self.assertIn("error", response)
        self.assertIn("jsonschema_errors", response)

    def test_new_execution_no_instance(self):
        payload = dict(self.payload)
        payload["instance_id"] = "bad_id"
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(404, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_executions(self):
        self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)

    def test_get_no_executions(self):
        self.get_no_rows(self.url)

    def test_get_executions_superadmin(self):
        self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)
        token = self.create_service_user()
        rows = self.client.get(
            self.url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        self.assertEqual(len(rows.json), len(self.payloads))


class TestExecutionRelaunchEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.url = EXECUTION_URL_NORUN
        self.model = ExecutionModel

        def load_file_fk(_file):
            with open(_file) as f:
                temp = json.load(f)
            temp["instance_id"] = fk_id
            return temp

        self.payload = load_file_fk(EXECUTION_PATH)

    def test_relaunch_execution(self):
        idx = self.create_new_row(self.url, self.model, payload=self.payload)

        # Add solution checks to see if they are deleted correctly
        token = self.create_service_user()
        self.update_row(
            url=DAG_URL + idx + "/",
            payload_to_check=dict(),
            change=dict(solution_schema="_data_checks", checks=dict(check_1=[])),
            token=token,
            check_payload=False,
        )

        url = EXECUTION_URL + idx + "/relaunch/?run=0"
        self.payload["config"]["warmStart"] = False
        response = self.client.post(
            url,
            data=json.dumps({"config": self.payload["config"]}),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(201, response.status_code)

        url = EXECUTION_URL + idx + "/data"
        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        ).json

        self.assertEqual(row["config"], self.payload["config"])
        self.assertIsNone(row["checks"])

    @patch("cornflow.endpoints.execution.Airflow")
    def test_relaunch_execution_run(self, af_client_class):
        patch_af_client(af_client_class)

        idx = self.create_new_row(self.url, self.model, payload=self.payload)

        # Add solution checks to see if they are deleted correctly
        token = self.create_service_user()
        self.update_row(
            url=DAG_URL + idx + "/",
            payload_to_check=dict(),
            change=dict(solution_schema="_data_checks", checks=dict(check_1=[])),
            token=token,
            check_payload=False,
        )

        url = EXECUTION_URL + idx + "/relaunch/"
        self.payload["config"]["warmStart"] = False
        response = self.client.post(
            url,
            data=json.dumps({"config": self.payload["config"]}),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(201, response.status_code)

        url = EXECUTION_URL + idx + "/data"
        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        ).json

        self.assertEqual(row["config"], self.payload["config"])
        self.assertIsNone(row["checks"])

    def test_relaunch_invalid_execution(self):
        idx = "thisIsAnInvalidExecutionId"
        url = EXECUTION_URL + idx + "/relaunch/?run=0"
        self.payload["config"]["warmStart"] = False
        response = self.client.post(
            url,
            data=json.dumps({"config": self.payload["config"]}),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(404, response.status_code)


class TestExecutionsDetailEndpointMock(CustomTestCase):
    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.model = ExecutionModel
        self.response_items = {
            "id",
            "name",
            "description",
            "created_at",
            "instance_id",
            "data_hash",
            "message",
            "state",
            "config",
            "schema",
            "user_id",
            "indicators",
            "username",
            "updated_at"
        }
        # we only check the following because this endpoint does not return data
        self.items_to_check = ["name", "description"]
        self.url = EXECUTION_URL
        with open(EXECUTION_PATH) as f:
            self.payload = json.load(f)
        self.payload["instance_id"] = fk_id


class TestExecutionsDetailEndpoint(
    TestExecutionsDetailEndpointMock, BaseTestCases.DetailEndpoint
):
    def setUp(self):
        super().setUp()
        self.query_arguments = {"run": 0}

    # TODO: this test should be moved as it is not using the detail endpoint
    def test_incomplete_payload2(self):
        payload = {"description": "arg", "instance_id": self.payload["instance_id"]}
        response = self.create_new_row(
            self.url + "?run=0",
            self.model,
            payload,
            expected_status=400,
            check_payload=False,
        )

    def test_create_delete_instance_load(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        keys_to_check = [
            "message",
            "id",
            "schema",
            "data_hash",
            "config",
            "instance_id",
            "user_id",
            "indicators",
            "description",
            "name",
            "created_at",
            "state",
            "username",
            "updated_at"
        ]
        execution = self.get_one_row(
            self.url + idx,
            payload={**self.payload, **dict(id=idx)},
            keys_to_check=keys_to_check,
        )
        self.delete_row(self.url + idx + "/")
        keys_to_check = [
            "id",
            "schema",
            "description",
            "name",
            "user_id",
            "executions",
            "created_at",
            "data_hash",
        ]
        instance = self.get_one_row(
            INSTANCE_URL + execution["instance_id"] + "/",
            payload={},
            expected_status=200,
            check_payload=False,
            keys_to_check=keys_to_check,
        )
        executions = [execution["id"] for execution in instance["executions"]]
        self.assertFalse(idx in executions)

    def test_delete_instance_deletes_execution(self):
        # we create a new instance
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        payload = {**self.payload, **dict(instance_id=fk_id)}
        # we create an execution for that instance
        idx = self.create_new_row(self.url + "?run=0", self.model, payload)
        self.get_one_row(self.url + idx, payload={**self.payload, **dict(id=idx)})
        # we delete the new instance
        self.delete_row(INSTANCE_URL + fk_id + "/")
        # we check the execution does not exist
        self.get_one_row(
            self.url + idx, payload={}, expected_status=404, check_payload=False
        )

    def test_update_one_row_data(self):
        idx = self.create_new_row(
            self.url_with_query_arguments(), self.model, self.payload
        )
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        payload["data"]["parameters"]["name"] = "NewName"

        url = self.url + str(idx) + "/"
        payload = {
            **self.payload,
            **dict(id=idx, name="new_name", data=payload["data"]),
        }
        self.update_row(
            url,
            dict(name="new_name", data=payload["data"]),
            payload,
        )

        url += "data/"
        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )

        self.assertEqual(row.json["checks"], None)

    @patch("cornflow.endpoints.execution.Airflow")
    def test_stop_execution(self, af_client_class):
        patch_af_client(af_client_class)

        idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)

        response = self.client.post(
            self.url + str(idx) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json["message"], "The execution has been stopped")


class TestExecutionsDataEndpoint(TestExecutionsDetailEndpointMock):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "data"}
        self.items_to_check = ["name"]
        self.keys_to_check = [
            "created_at",
            "checks",
            "instance_id",
            "schema",
            "data",
            "user_id",
            "message",
            "data_hash",
            "log",
            "config",
            "description",
            "state",
            "name",
            "id",
        ]

    def test_get_one_execution(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        self.url = EXECUTION_URL + idx + "/data/"
        payload = dict(self.payload)
        payload["id"] = idx
        self.get_one_row(self.url, payload, keys_to_check=self.keys_to_check)

    def test_get_one_execution_superadmin(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        token = self.create_service_user()
        self.get_one_row(
            EXECUTION_URL + idx + "/data/",
            payload,
            token=token,
            keys_to_check=self.keys_to_check,
        )


class TestExecutionsLogEndpoint(TestExecutionsDetailEndpointMock):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "log", "indicators"}
        self.items_to_check = ["name"]
        self.keys_to_check = [
            "created_at",
            "id",
            "log_text",
            "instance_id",
            "state",
            "message",
            "description",
            "data_hash",
            "name",
            "log",
            "schema",
            "user_id",
            "config",
            "indicators",
            "username",
            "updated_at"
        ]

    def test_get_one_execution(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        self.get_one_row(
            EXECUTION_URL + idx + "/log/", payload, keys_to_check=self.keys_to_check
        )

    def test_get_one_execution_superadmin(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        token = self.create_service_user()
        self.get_one_row(
            EXECUTION_URL + idx + "/log/",
            payload,
            token=token,
            keys_to_check=self.keys_to_check,
        )


class TestExecutionsStatusEndpoint(TestExecutionsDetailEndpointMock):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "status"}
        self.items_to_check = []

    @patch("cornflow.endpoints.execution.Airflow")
    def test_get_one_status(self, af_client_class):
        patch_af_client(af_client_class)

        idx = self.create_new_row(EXECUTION_URL, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        keys_to_check = ["state", "message", "id", "data_hash"]
        data = self.get_one_row(
            EXECUTION_URL + idx + "/status/",
            payload,
            check_payload=False,
            keys_to_check=keys_to_check,
        )
        self.assertEqual(data["state"], 1)

    @patch("cornflow.endpoints.execution.Airflow")
    def test_put_one_status(self, af_client_class):
        patch_af_client(af_client_class)

        idx = self.create_new_row(EXECUTION_URL, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        response = self.client.put(
            EXECUTION_URL + idx + "/status/",
            data=json.dumps({"status": 0}),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(f"execution {idx} updated correctly", response.json["message"])


class TestExecutionsModel(TestExecutionsDetailEndpointMock):
    def test_repr_method(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.repr_method(idx, f"<Execution {idx}>")

    def test_str_method(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.str_method(idx, f"<Execution {idx}>")
