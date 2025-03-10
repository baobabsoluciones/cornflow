"""
Unit test for the instances endpoints
"""

# Import from libraries
import hashlib
import json
import zlib

# Import from internal modules
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.shared.utils import hash_json_256
from cornflow.tests.const import (
    EXECUTION_URL_NORUN,
    EXECUTION_PATH,
    INSTANCE_URL,
    INSTANCES_LIST,
    INSTANCE_PATH,
    EMPTY_INSTANCE_PATH
)
from cornflow.tests.custom_test_case import CustomTestCase, BaseTestCases
from flask import current_app


class TestInstancesListEndpoint(BaseTestCases.ListFilters):
    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        self.response_items = {"id", "name", "description", "created_at", "schema"}
        self.items_to_check = ["name", "description", "schema"]

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)
        self.payload2 = load_file(EMPTY_INSTANCE_PATH)
        self.payloads = [load_file(f) for f in INSTANCES_LIST]
        self.keys_to_check = [
            "data_hash",
            "created_at",
            "schema",
            "description",
            "id",
            "user_id",
            "name",
        ]

    def test_new_instance(self):
        self.create_new_row(self.url, self.model, self.payload)

    def test_empty_instance(self):
        """
        testing what happend when empty dictionary get saved
        """
        self.create_new_row(self.url, self.model, self.payload2)

        active_rows = self.model.query.filter(self.model.deleted_at == None).all()
        has_empty_dict = any(getattr(row, "data", None) == {} for row in active_rows)
        self.assertTrue(has_empty_dict, "Error: Not an empty dicctionary")

    def test_new_instance_missing_info(self):
        del self.payload["data"]["parameters"]
        self.create_new_row(
            self.url, self.model, self.payload, expected_status=400, check_payload=False
        )

    def test_new_instance_extra_info(self):
        self.payload["data"]["additional_param"] = 1
        self.create_new_row(self.url, self.model, self.payload)

    def test_new_instance_bad_format(self):
        payload = dict(data1=1, data2=dict(a=1))
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_instances(self):
        self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)

    def test_get_instances_superadmin(self):
        self.get_rows(self.url, self.payloads, keys_to_check=self.keys_to_check)
        token = self.create_service_user()
        rows = self.client.get(
            self.url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        self.assertEqual(len(rows.json), len(self.payloads))

    def test_get_no_instances(self):
        self.get_no_rows(self.url)

    def test_hash(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        response = self.client.get(
            INSTANCE_URL + id + "/", headers=self.get_header_with_auth(self.token)
        )
        self.assertEqual(
            response.json["data_hash"],
            "4e1ad86aa70efc6e588744aa4b2300cb9aea516b6bea9355bd00c50dac1ee6a2",
        )

    def test_hash2(self):
        # The string / hash pair was taken from: https://reposhub.com/javascript/security/feross-simple-sha256.html
        str_data = hashlib.sha256("hey there".encode("utf-8")).hexdigest()
        self.assertEqual(
            str_data, "74ef874a9fa69a86e091ea6dc2668047d7e102d518bebed19f8a3958f664e3da"
        )

    def test_hash3(self):
        str_data = json.dumps(
            self.payload["data"], sort_keys=True, separators=(",", ":")
        )
        _hash = hashlib.sha256(str_data.encode("utf-8")).hexdigest()
        self.assertEqual(
            _hash, "4e1ad86aa70efc6e588744aa4b2300cb9aea516b6bea9355bd00c50dac1ee6a2"
        )

    def test_hash4(self):
        str_object = hash_json_256({"hello": "goodbye", "123": 456})
        self.assertEqual(
            str_object,
            "72804f4e0847a477ee69eae4fbf404b03a6c220bacf8d5df34c964985acd473f",
        )


class TestInstancesDetailEndpointBase(CustomTestCase):
    def setUp(self):
        super().setUp()
        # the order of the following three lines *is important*
        # to create the instance and *then* update the url
        self.url = INSTANCE_URL
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)
        self.response_items = {
            "id",
            "name",
            "description",
            "created_at",
            "user_id",
            "executions",
            "data_hash",
            "schema",
        }
        # we only check name and description because this endpoint does not return data
        self.items_to_check = ["name", "description", "schema"]


class TestInstancesDetailEndpoint(
    TestInstancesDetailEndpointBase, BaseTestCases.DetailEndpoint
):
    def test_update_one_row_data(self):
        idx = self.create_new_row(
            self.url_with_query_arguments(), self.model, self.payload
        )
        self.payload["data"]["parameters"]["name"] = "NewName"
        url = self.url + str(idx) + "/"
        payload = {
            **self.payload,
            **dict(id=idx, name="new_name", data=self.payload["data"]),
        }
        self.update_row(
            url,
            dict(name="new_name", data=self.payload["data"]),
            payload,
        )

        url += "data/"
        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )

        self.assertIsNone(row.json["checks"], None)


class TestInstancesDataEndpoint(TestInstancesDetailEndpointBase):
    def setUp(self):
        super().setUp()
        self.response_items.add("data")
        self.response_items.add("checks")
        self.response_items.remove("executions")
        self.items_to_check += ["data", "checks"]

    def test_get_one_instance(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=idx)}
        keys_to_check = [
            "data",
            "id",
            "schema",
            "data_hash",
            "user_id",
            "description",
            "name",
            "checks",
            "created_at",
        ]
        result = self.get_one_row(
            INSTANCE_URL + idx + "/data/", payload, keys_to_check=keys_to_check
        )
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_instance_compression(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Accept-Encoding": "gzip",
        }
        response = self.client.get(INSTANCE_URL + idx + "/data/", headers=headers)
        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        raw = zlib.decompress(response.data, 16 + zlib.MAX_WBITS).decode("utf-8")
        response = json.loads(raw)
        self.assertEqual(self.payload["data"], response["data"])
        # self.assertEqual(resp.headers[], 'br')

    def test_get_one_instance_superadmin(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_service_user()
        payload = {**self.payload, **dict(id=idx)}
        self.get_one_row(INSTANCE_URL + idx + "/data/", payload, token=token)

    def test_get_none_instance_planner_one(self):
        # Test planner users cannot access objects of other users
        idx = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_planner()

        self.get_one_row(
            INSTANCE_URL + idx + "/data/",
            payload=None,
            expected_status=404,
            check_payload=False,
            token=token,
            keys_to_check=["error"],
        )

    def test_get_none_instance_planner_all(self):
        # Test planner users cannot access objects of other users
        self.create_new_row(self.url, self.model, self.payload)
        token = self.create_planner()
        self.get_no_rows(INSTANCE_URL, token=token)


class TestAccessPlannerUsers(CustomTestCase):
    def setUp(self):
        super().setUp()

        current_app.config["USER_ACCESS_ALL_OBJECTS"] = 1
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)
        self.url = INSTANCE_URL
        self.model = InstanceModel

    def test_get_one_instance_planner(self):
        # Test planner users can access objects of other users
        idx = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_planner()
        payload = {**self.payload, **dict(id=idx)}
        keys_to_check = [
            "data",
            "id",
            "schema",
            "data_hash",
            "user_id",
            "description",
            "name",
            "checks",
            "created_at",
        ]
        self.get_one_row(
            INSTANCE_URL + idx + "/data/",
            payload,
            token=token,
            keys_to_check=keys_to_check,
        )

    def test_get_all_instance_planner(self):
        # Test planner users can access objects of other users
        self.create_new_row(self.url, self.model, self.payload)
        token = self.create_planner()
        row = self.client.get(
            INSTANCE_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

        self.assertEqual(200, row.status_code)
        self.assertEqual(len(row.json), 1)


class TestInstanceModelMethods(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    def test_execution_delete_cascade(self):
        with open(EXECUTION_PATH) as f:
            payload = json.load(f)

        self.cascade_delete(
            self.url,
            self.model,
            self.payload,
            EXECUTION_URL_NORUN,
            ExecutionModel,
            payload,
            "instance_id",
        )

    def test_repr_method(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(idx, f"<Instance {idx}>")

    def test_str_method(self):
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(idx, f"<Instance {idx}>")
