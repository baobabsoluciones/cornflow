import json
from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
INSTANCES_LIST = [INSTANCE_PATH, './cornflow/tests/data/new_instance_2.json']


class TestInstancesListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
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
        # TODO: here we get 5 >= 2. But this depends on the order of the tests...
        #  we should do something to really check the correct number
        self.assertGreaterEqual(len(rows.json), len(INSTANCES_LIST))

    def test_get_no_instances(self):
        self.get_no_rows(self.url)


class TestInstancesDetailEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        # the order of the following three lines *is important*
        # to create the instance and *then* update the url
        self.url = '/instance/'
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)
        self.response_items = {'id', 'name', 'description', 'created_at', 'user_id', 'executions'}
        # we only check name and description because this endpoint does not return data
        self.items_to_check = ['name', 'description']

    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row(self.url + id + '/', payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

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


class TestInstancesDataEndpoint(TestInstancesDetailEndpoint):

    def setUp(self):
        super().setUp()
        self.response_items = {'id', 'name', 'data'}
        self.items_to_check = ['name', 'data']

    def test_get_one_instance(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        payload = {**self.payload, **dict(id=id)}
        result = self.get_one_row('/instance/' + id + '/data/', payload)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_update_one_instance(self):
        pass

    def test_delete_one_instance(self):
        pass


class TestInstanceModelMethods(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel
        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    # TODO: should these test be implemented? The functions that these test should cover are already covered
    #  by other test cases, mainly the endpoint functions that use this functions
    def test_save(self):
        pass

    def test_update(self):
        pass

    def test_disable(self):
        pass

    def test_delete(self):
        pass

    def test_get_all_instances(self):
        pass

    def test_get_one_instance_from_id(self):
        pass

    def test_get_one_instance_from_user(self):
        pass

    def test_repr_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(id, '<id {}>'.format(id))

    def test_str_method(self):
        id = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(id, '<id {}>'.format(id))

