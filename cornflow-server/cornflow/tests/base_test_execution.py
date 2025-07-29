# Import from libraries
import json
from unittest.mock import patch

from cornflow.app import create_app

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
    EDIT_EXECUTION_SOLUTION,
    CUSTOM_CONFIG_PATH,
)
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
from cornflow.tests.unit.tools import patch_af_client, patch_db_client
from abc import ABC, abstractmethod


class TestExecutionsDetailEndpointMock(CustomTestCase):

    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.instance_payload = payload
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

class BaseExecutionList(BaseTestCases.ListFilters, ABC):

    @property
    @abstractmethod
    def orchestrator_patch_target(self):
        """Must be implemented by concrete classes"""
        pass

    @property
    @abstractmethod
    def orchestrator_patch_fn(self):
        """Must be implemented by concrete classes"""
        pass

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
            "first_name",
            "last_name",
            "updated_at",
        ]

    def patch_orchestrator(self, client_class):
        if self.orchestrator_patch_fn:
            self.orchestrator_patch_fn(client_class)

    def test_new_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.create_new_row(self.url, self.model, payload=self.payload)

    def test_get_custom_config(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            id = self.create_new_row(
                self.url, self.model, payload=self.custom_config_payload
            )
            url = EXECUTION_URL + "/" + str(id) + "/" + "?run=0"

            response = self.get_one_row(
                url,
                payload={**self.custom_config_payload, **dict(id=id)},
            )
            self.assertEqual(response["config"]["block_model"]["solver"], "mip.gurobi")

    def test_new_execution_run(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)

    def test_new_execution_bad_config(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            response = self.create_new_row(
                EXECUTION_URL,
                self.model,
                payload=self.bad_payload,
                expected_status=400,
                check_payload=False,
            )
            self.assertIn("error", response)
            self.assertIn("jsonschema_errors", response)

    def test_new_execution_partial_config(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.payload["config"].pop("solver")
            response = self.create_new_row(
                EXECUTION_URL, self.model, payload=self.payload, check_payload=False
            )
            self.assertIn("solver", response["config"])
            self.assertEqual(response["config"]["solver"], "cbc")

    def test_new_execution_with_solution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.payload["data"] = self.solution
            response = self.create_new_row(
                EXECUTION_URL,
                self.model,
                payload=self.payload,
                check_payload=False,
            )

    def test_new_execution_with_solution_bad(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)

    def test_get_no_executions(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.get_no_rows(self.url)

    def test_get_executions_superadmin(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)
            token = self.create_service_user()
            rows = self.client.get(
                self.url,
                follow_redirects=True,
                headers=self.get_header_with_auth(token),
            )
            self.assertEqual(len(rows.json), len(self.payloads))


class BaseExecutionRelaunch(CustomTestCase, ABC):

    @property
    @abstractmethod
    def orchestrator_patch_target(self):
        """Must be implemented by concrete classes"""
        pass

    @property
    @abstractmethod
    def orchestrator_patch_fn(self):
        """Must be implemented by concrete classes"""
        pass

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

    def patch_orchestrator(self, client_class):
        if self.orchestrator_patch_fn:
            self.orchestrator_patch_fn(client_class)

    def test_relaunch_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
                url,
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            ).json

            self.assertEqual(row["config"], self.payload["config"])
            self.assertIsNone(row["checks"])

    def test_relaunch_execution_run(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
                url,
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            ).json

            self.assertEqual(row["config"], self.payload["config"])
            self.assertIsNone(row["checks"])

    def test_relaunch_invalid_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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


class BaseExecutionDetail(BaseTestCases.DetailEndpoint, ABC):

    @property
    @abstractmethod
    def orchestrator_patch_target(self):
        """Must be implemented by concrete classes"""
        pass

    @property
    @abstractmethod
    def orchestrator_patch_fn(self):
        """Must be implemented by concrete classes"""
        pass

    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.instance_payload = payload
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
            "first_name",
            "last_name",
            "updated_at",
        }
        # we only check the following because this endpoint does not return data
        self.items_to_check = ["name", "description"]
        self.url = EXECUTION_URL
        with open(EXECUTION_PATH) as f:
            self.payload = json.load(f)
        self.payload["instance_id"] = fk_id
        self.query_arguments = {"run": 0}

    def patch_orchestrator(self, client_class):
        if self.orchestrator_patch_fn:
            self.orchestrator_patch_fn(client_class)

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
            "first_name",
            "last_name",
            "updated_at",
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
        # this test should be agnostic of the orchestrator
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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
                url,
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

            self.assertEqual(row.json["checks"], None)

    def test_stop_execution(self):
        #! Feature to be implemented for databricks
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            # We only execute this test for airflow
            if (
                self.orchestrator_patch_target
                == "cornflow.endpoints.execution.Databricks"
            ):
                self.skipTest("This feature is not implemented for databricks")

            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)

            response = self.client.post(
                self.url + str(idx) + "/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(response.json["message"], "The execution has been stopped")

    def test_edit_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            id_new_instance = self.create_new_row(
                INSTANCE_URL, InstanceModel, self.instance_payload
            )
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )

            # Extract the data from data/edit_execution_solution.json
            with open(EDIT_EXECUTION_SOLUTION) as f:
                data = json.load(f)

            data = {
                "name": "new_name",
                "description": "Updated description",
                "data": data,
                "instance_id": id_new_instance,
            }
            payload_to_check = {
                "id": idx,
                "name": "new_name",
                "description": "Updated description",
                "data_hash": "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b",
                "instance_id": "805bad3280c95e45384dc6bd91a41317f9a7858c",
            }
            self.update_row(
                self.url + str(idx) + "/",
                data,
                payload_to_check,
            )

    def test_get_one_status(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)
            payload = dict(self.payload)
            payload["id"] = idx
            keys_to_check = ["state", "message", "id", "data_hash"]
            data = self.get_one_row(
                EXECUTION_URL + idx + "/status/",
                payload,
                check_payload=False,
                keys_to_check=keys_to_check,
            )
            # In the patch we assign success as the state
            self.assertEqual(data["state"], 1)

    def test_put_one_status(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)
            payload = dict(self.payload)
            payload["id"] = idx
            response = self.client.put(
                EXECUTION_URL + idx + "/status/",
                data=json.dumps({"status": 0}),
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(
                f"execution {idx} updated correctly", response.json["message"]
            )


class BaseExecutionData(TestExecutionsDetailEndpointMock, ABC):
    # e.g. "cornflow.endpoints.execution.Airflow"
    orchestrator_patch_target = None
    # e.g. patch_af_client
    orchestrator_patch_fn = None

    def setUp(self):
        super().setUp()
        self.response_items = {
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
            "indicators",
            "updated_at",
            "username",
        }
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

    def patch_orchestrator(self, client_class):
        """Patch the orchestrator client for testing"""
        if self.orchestrator_patch_fn:
            self.orchestrator_patch_fn(client_class)

    def test_get_one_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
            self.url = EXECUTION_URL + idx + "/data/"
            payload = dict(self.payload)
            payload["id"] = idx
            self.get_one_row(self.url, payload, keys_to_check=self.keys_to_check)

    def test_get_one_execution_superadmin(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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


class BaseExecutionLog(BaseExecutionDetail, ABC):
    # e.g. "cornflow.endpoints.execution.Airflow"
    orchestrator_patch_target = None
    # e.g. patch_af_client
    orchestrator_patch_fn = None

    def setUp(self):
        super().setUp()
        # response_items for the log endpoint specifically
        self.log_response_items = {
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
            "indicators",
            "updated_at",
            "username",
            "first_name",
            "last_name",
            "log",
            "log_text",
        }
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
            "first_name",
            "last_name",
            "updated_at",
        ]

    def test_get_one_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
            payload = dict(self.payload)
            payload["id"] = idx
            self.get_one_row(
                EXECUTION_URL + idx + "/log/", payload, keys_to_check=self.keys_to_check
            )

    def test_get_one_execution_superadmin(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
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


class BaseExecutionModel(BaseExecutionDetail, ABC):
    # e.g. "cornflow.endpoints.execution.Airflow"
    orchestrator_patch_target = None
    # e.g. patch_af_client
    orchestrator_patch_fn = None

    def test_repr_method(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
            self.repr_method(idx, f"<Execution {idx}>")

    def test_str_method(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
            self.str_method(idx, f"<Execution {idx}>")


class BaseExecutionStatus(BaseExecutionDetail, ABC):
    # e.g. "cornflow.endpoints.execution.Airflow"
    orchestrator_patch_target = None
    # e.g. patch_af_client
    orchestrator_patch_fn = None

    def setUp(self):
        super().setUp()

    def test_get_one_status(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)
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

    def test_put_one_status(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)
            payload = dict(self.payload)
            payload["id"] = idx
            response = self.client.put(
                EXECUTION_URL + idx + "/status/",
                data=json.dumps({"status": 0}),
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(
                f"execution {idx} updated correctly", response.json["message"]
            )
