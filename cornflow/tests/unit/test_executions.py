from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
import json
from cornflow.tests.const import (
    INSTANCE_PATH,
    EXECUTION_PATH,
    EXECUTIONS_LIST,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_URL,
)

# TODO: tests of the dag endpoint (put, post)


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
        self.payloads = [load_file_fk(f) for f in EXECUTIONS_LIST]

    def test_new_execution(self):
        self.create_new_row(self.url, self.model, payload=self.payload)

    def test_new_execution_no_instance(self):
        payload = dict(self.payload)
        payload["instance_id"] = "bad_id"
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_executions(self):
        self.get_rows(self.url, self.payloads)

    def test_get_no_executions(self):
        self.get_no_rows(self.url)

    def test_get_executions_superadmin(self):
        self.get_rows(self.url, self.payloads)
        token = self.create_super_admin()
        rows = self.client.get(
            self.url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        self.assertEqual(len(rows.json), len(self.payloads))


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
        }
        # we only check the following because this endpoint does not return data
        self.items_to_check = ["name", "description"]
        self.url = EXECUTION_URL
        with open(EXECUTION_PATH) as f:
            self.payload = json.load(f)
        self.payload["instance_id"] = fk_id


class TestExecutionsDetailEndpoint(TestExecutionsDetailEndpointMock):
    def test_get_nonexistent_execution(self):
        result = self.get_one_row(
            self.url + "some_key_" + "/", {}, expected_status=404, check_payload=False
        )
        return result

    def test_get_one_execution(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        result = self.get_one_row(self.url + idx, payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_incomplete_payload(self):
        payload = {"description": "arg"}
        response = self.create_new_row(
            self.url + "?run=0",
            self.model,
            payload,
            expected_status=400,
            check_payload=False,
        )

    def test_incomplete_payload2(self):
        payload = {"description": "arg", "instance_id": self.payload["instance_id"]}
        response = self.create_new_row(
            self.url + "?run=0",
            self.model,
            payload,
            expected_status=400,
            check_payload=False,
        )

    def test_payload_bad_format(self):
        payload = {"name": 1}
        response = self.create_new_row(
            self.url + "?run=0",
            self.model,
            payload,
            expected_status=400,
            check_payload=False,
        )

    def test_delete_one_execution(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.delete_row(self.url + idx + "/")
        self.get_one_row(
            self.url + idx, payload={}, expected_status=404, check_payload=False
        )

    def test_update_one_execution(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        payload = {**self.payload, **dict(id=idx, name="new_name")}
        self.update_row(self.url + idx + "/", dict(name="new_name"), payload)

    def test_update_one_execution_bad_format(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.update_row(
            self.url + idx + "/",
            dict(instance_id="some_id"),
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_create_delete_instance_load(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        execution = self.get_one_row(
            self.url + idx, payload={**self.payload, **dict(id=idx)}
        )
        self.delete_row(self.url + idx + "/")
        instance = self.get_one_row(
            INSTANCE_URL + execution["instance_id"] + "/",
            payload={},
            expected_status=200,
            check_payload=False,
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

    def test_get_one_execution_superadmin(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        token = self.create_super_admin()
        self.get_one_row(
            self.url + idx + "/", {**self.payload, **dict(id=idx)}, token=token
        )

    def test_edit_one_execution(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        payload = {**self.payload, **dict(id=idx, name="new_name")}
        self.update_row(self.url + idx + "/", dict(name="new_name"), payload)


class TestExecutionsDataEndpoint(TestExecutionsDetailEndpointMock):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "data"}
        self.items_to_check = ["name"]

    def test_get_one_execution(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        self.url = EXECUTION_URL + idx + "/data/"
        payload = dict(self.payload)
        payload["id"] = idx
        self.get_one_row(self.url, payload)

    def test_get_one_execution_superadmin(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        token = self.create_super_admin()
        self.get_one_row(EXECUTION_URL + idx + "/data/", payload, token=token)


class TestExecutionsLogEndpoint(TestExecutionsDetailEndpointMock):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "log"}
        self.items_to_check = ["name"]

    def test_get_one_execution(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        self.get_one_row(EXECUTION_URL + idx + "/log/", payload)

    def test_get_one_execution_superadmin(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        payload = dict(self.payload)
        payload["id"] = idx
        token = self.create_super_admin()
        self.get_one_row(EXECUTION_URL + idx + "/log/", payload, token=token)


class TestExecutionsModel(TestExecutionsDetailEndpointMock):
    def test_repr_method(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.repr_method(idx, "<id {}>".format(idx))

    def test_str_method(self):
        idx = self.create_new_row(self.url + "?run=0", self.model, self.payload)
        self.str_method(idx, "<id {}>".format(idx))
