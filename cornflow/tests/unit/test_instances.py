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

    def test_new_instance(self):
        self.create_new_row(INSTANCE_PATH)

    def test_new_instance_bad_format(self):
        payload = dict(data1= 1, data2=dict(a=1))
        response = self.client.post(self.url, data=json.dumps(payload), follow_redirects=True,
                                    headers={"Content-Type": "application/json",
                                             "Authorization": 'Bearer ' + self.token})
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_instances(self):
        self.get_rows(INSTANCES_LIST)

    def test_get_no_instances(self):
        self.get_no_rows()


class TestInstancesDetailEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        # the order of the following three lines *is important*
        # to create the instance and *then* update the url
        self.url = '/instance/'
        self.model = InstanceModel
        # TODO: instead of this, we should create an instance with the models
        self.id = self.create_new_row(INSTANCE_PATH)
        self.url = self.url + self.id + '/'
        self.response_items = {'id', 'name', 'description', 'created_at', 'executions'}
        # we only check name and description because this endpoint does not return data
        self.items_to_check = ['name', 'description']

    def test_get_one_instance(self):
        result = self.get_one_row(INSTANCE_PATH)
        dif = self.response_items.symmetric_difference(result.keys())
        self.assertEqual(len(dif), 0)

    def test_update_one_instance(self):
        self.update_row(INSTANCE_PATH, 'name', 'new_name')

    def test_delete_one_instance(self):
        self.delete_row()


class TestInstancesDataEndpoint(TestInstancesDetailEndpoint):

    def setUp(self):
        super().setUp()
        self.url = '/instance/' + self.id + '/data/'
        self.response_items = {'id', 'name', 'data'}
        self.items_to_check = ['name', 'data']

    def test_get_one_instance(self):
        result = self.get_one_row(INSTANCE_PATH)
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
        self.id = self.create_new_row(INSTANCE_PATH)

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
        self.repr_method('<id {}>'.format(self.id))

    def test_str_method(self):
        self.str_method('<id {}>'.format(self.id))

