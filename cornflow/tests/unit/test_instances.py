import json
import zlib
from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import INSTANCE_URL, INSTANCES_LIST, INSTANCE_PATH


class TestInstancesListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        self.response_items = {'id', 'name', 'description', 'created_at'}
        self.items_to_check = ['name', 'description']

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)
        self.payloads = [load_file(f) for f in INSTANCES_LIST]

    def test_new_instance(self):
        self.create_new_row(self.url, self.model, self.payload)

    def test_new_instance_missing_info(self):
        del self.payload['data']['parameters']
        self.create_new_row(self.url, self.model, self.payload, expected_status=400, check_payload=False)

    def test_new_instance_extra_info(self):
        self.payload['data']['additional_param'] = 1
        self.create_new_row(self.url, self.model, self.payload)

    def test_new_instance_bad_format(self):
        payload = dict(data1= 1, data2=dict(a=1))
        response = self.client.post(self.url, data=json.dumps(payload), follow_redirects=True,
                                    headers={"Content-Type": "application/json",
                                             "Authorization": 'Bearer ' + self.token})
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_instances(self):
        self.get_rows(self.url, self.payloads)

    def test_get_instances_superadmin(self):
        self.get_rows(self.url, self.payloads)
        token = self.create_super_admin()
        rows = self.client.get(self.url, follow_redirects=True,
                               headers=self.get_header_with_auth(token))
        self.assertEqual(len(rows.json), len(self.payloads))

    def test_get_no_instances(self):
        self.get_no_rows(self.url)


class TestInstancesDetailEndpointBase(CustomTestCase):

    def setUp(self):
        super().setUp()
        # the order of the following three lines *is important*
        # to create the instance and *then* update the url
        self.url = INSTANCE_URL
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)
        self.response_items = {'id', 'name', 'description', 'created_at', 'user_id', 'executions'}
        # we only check name and description because this endpoint does not return data
        self.items_to_check = ['name', 'description']


class TestInstancesDetailEndpoint(TestInstancesDetailEndpointBase):

    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(self.url + id + '/', payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_get_one_instance_superadmin(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        token = self.create_super_admin()
        self.get_one_row(self.url + id + '/', {**self.payload, **dict(id=id)}, token=token)

    def test_update_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id, name='new_name')}
        self.update_row(self.url + id + '/', dict(name='new_name'), payload)

    def test_update_one_instance_bad_format(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.update_row(self.url + id + '/', dict(instance_id='some_id'), {},
                        expected_status=400, check_payload=False)

    def test_delete_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.delete_row(self.url + id + '/', self.model)

    def test_get_nonexistent_instance(self):
        result = self.get_one_row(self.url + 'some_key_' + '/', {},
                                  expected_status=404, check_payload=False)


class TestInstancesDataEndpoint(TestInstancesDetailEndpointBase):

    def setUp(self):
        super().setUp()
        self.response_items = {'id', 'name', 'data'}
        self.items_to_check = ['name', 'data']

    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(INSTANCE_URL + id + '/data/', payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_instance_compression(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        headers =\
            {"Content-Type": "application/json",
             "Authorization": 'Bearer ' + self.token,
             'Accept-Encoding': 'gzip'}
        response = self.client.get(INSTANCE_URL + id + '/data/', headers=headers)
        self.assertEqual(response.headers['Content-Encoding'], 'gzip')
        raw = zlib.decompress(response.data, 16+zlib.MAX_WBITS).decode("utf-8")
        response = json.loads(raw)
        self.assertEqual(self.payload['data'], response['data'])
        # self.assertEqual(resp.headers[], 'br')

class TestInstanceModelMethods(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    def test_repr_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(id, '<id {}>'.format(id))

    def test_str_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(id, '<id {}>'.format(id))

