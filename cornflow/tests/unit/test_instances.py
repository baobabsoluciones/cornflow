import json
import zlib
import hashlib
from cornflow.shared.utils import hash_json_256
from datetime import datetime, timedelta
from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import INSTANCE_URL, INSTANCES_LIST, INSTANCE_PATH

try:
    date_from_str = datetime.fromisoformat
except:

    def date_from_str(_string):
        return datetime.strptime(_string, "%Y-%m-%d %H:%M:%S.%f")


class TestInstancesListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        self.response_items = {"id", "name", "description", "created_at"}
        self.items_to_check = ["name", "description"]

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)
        self.payloads = [load_file(f) for f in INSTANCES_LIST]

    def test_new_instance(self):
        self.create_new_row(self.url, self.model, self.payload)

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
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_instances(self):
        self.get_rows(self.url, self.payloads)

    def test_get_instances_superadmin(self):
        self.get_rows(self.url, self.payloads)
        token = self.create_super_admin()
        rows = self.client.get(
            self.url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        self.assertEqual(len(rows.json), len(self.payloads))

    def test_get_no_instances(self):
        self.get_no_rows(self.url)

    def test_opt_filters_limit(self):
        # we create 4 instances
        data_many = [self.payload for i in range(4)]
        allrows = self.get_rows(self.url, data_many)
        self.apply_filter(self.url, dict(limit=1), [allrows.json[0]])

    def test_opt_filters_offset(self):
        # we create 4 instances
        data_many = [self.payload for i in range(4)]
        allrows = self.get_rows(self.url, data_many)
        self.apply_filter(self.url, dict(offset=1, limit=2), allrows.json[1:3])

    def test_opt_filters_date_lte(self):
        # we create 4 instances
        data_many = [self.payload for i in range(4)]
        allrows = self.get_rows(self.url, data_many)

        a = date_from_str(allrows.json[0]["created_at"])
        b = date_from_str(allrows.json[1]["created_at"])
        date_limit = b + (a - b) / 2
        # we ask for one before the last one => we get the second from the last
        self.apply_filter(
            self.url,
            dict(creation_date_lte=date_limit.isoformat(), limit=1),
            [allrows.json[1]],
        )

    def test_opt_filters_date_gte(self):
        # we create 4 instances
        data_many = [self.payload for i in range(4)]
        allrows = self.get_rows(self.url, data_many)

        date_limit = date_from_str(allrows.json[2]["created_at"]) + timedelta(
            microseconds=1
        )
        # we ask for all after the third from the last => we get the last two
        self.apply_filter(
            self.url, dict(creation_date_gte=date_limit.isoformat()), allrows.json[:2]
        )
        return

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
        }
        # we only check name and description because this endpoint does not return data
        self.items_to_check = ["name", "description"]


class TestInstancesDetailEndpoint(TestInstancesDetailEndpointBase):
    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(self.url + id + "/", payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_get_one_instance_superadmin(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_super_admin()
        self.get_one_row(
            self.url + id + "/", {**self.payload, **dict(id=id)}, token=token
        )

    def test_update_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id, name="new_name")}
        self.update_row(self.url + id + "/", dict(name="new_name"), payload)

    def test_update_one_instance_bad_format(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.update_row(
            self.url + id + "/",
            dict(instance_id="some_id"),
            {},
            expected_status=400,
            check_payload=False,
        )

    def test_delete_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.delete_row(self.url + id + "/")

    def test_get_nonexistent_instance(self):
        result = self.get_one_row(
            self.url + "some_key_" + "/", {}, expected_status=404, check_payload=False
        )


class TestInstancesDataEndpoint(TestInstancesDetailEndpointBase):
    def setUp(self):
        super().setUp()
        self.response_items = {"id", "name", "data", "data_hash"}
        self.items_to_check = ["name", "data"]

    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(INSTANCE_URL + id + "/data/", payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_instance_compression(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.token,
            "Accept-Encoding": "gzip",
        }
        response = self.client.get(INSTANCE_URL + id + "/data/", headers=headers)
        self.assertEqual(response.headers["Content-Encoding"], "gzip")
        raw = zlib.decompress(response.data, 16 + zlib.MAX_WBITS).decode("utf-8")
        response = json.loads(raw)
        self.assertEqual(self.payload["data"], response["data"])
        # self.assertEqual(resp.headers[], 'br')

    def test_get_one_instance_superadmin(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_super_admin()
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(INSTANCE_URL + id + "/data/", payload, token=token)


class TestInstanceModelMethods(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    def test_repr_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(id, "<id {}>".format(id))

    def test_str_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(id, "<id {}>".format(id))
