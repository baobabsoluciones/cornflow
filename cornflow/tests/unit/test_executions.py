from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
import json


INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
EXECUTION_PATH = './cornflow/tests/data/new_execution.json'
EXECUTIONS_LIST = [EXECUTION_PATH, './cornflow/tests/data/new_execution_2.json']


class TestExecutionsListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row('/instance/', InstanceModel, payload)
        self.url = '/execution/?run=0'
        self.model = ExecutionModel

        def load_file_fk(_file):
            with open(_file) as f:
                temp = json.load(f)
            temp['instance_id'] = fk_id
            return temp

        self.payload = load_file_fk(EXECUTION_PATH)
        self.payloads = [load_file_fk(f) for f in EXECUTIONS_LIST]

    def test_new_execution(self):
        self.create_new_row(self.url, self.model, payload=self.payload)

    def test_new_execution_no_instance(self):
        payload = dict(self.payload)
        payload['instance_id'] = 'bad_id'
        response = self.client.post(self.url, data=json.dumps(payload), follow_redirects=True,
                                    headers=self.get_header_with_auth(self.token))
        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_executions(self):
        self.get_rows(self.url, self.payloads)

    def test_get_no_executions(self):
        self.get_no_rows(self.url)


class TestExecutionsDetailEndpointMock(CustomTestCase):

    def setUp(self):
        super().setUp()
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row('/instance/', InstanceModel, payload)
        self.model = ExecutionModel
        self.response_items = {'id', 'name', 'description', 'created_at', 'instance_id', 'finished'}
        # we only the following because this endpoint does not return data
        self.items_to_check = ['name', 'description']
        self.url = '/execution/'
        with open(EXECUTION_PATH) as f:
            self.payload = json.load(f)
        self.payload['instance_id'] = fk_id

class TestExecutionsDetailEndpoint(TestExecutionsDetailEndpointMock):

    def test_get_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        payload = dict(self.payload)
        payload['id'] = id
        self.get_one_row(self.url + id, payload)

    def test_delete_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        self.delete_row(self.url + id + '/', self.model)
        self.get_one_row(self.url + id, payload={}, expected_status=404, check_payload=False)

    def test_update_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        payload = {**self.payload, **dict(id=id, name='new_name')}
        self.update_row(self.url + id + '/', dict(name='new_name'), payload)

    def test_create_delete_instance_load(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        execution = self.get_one_row(self.url + id, payload={**self.payload, **dict(id=id)})
        self.delete_row(self.url + id + '/', self.model)
        instance = self.get_one_row('/instance/' + execution['instance_id'] + '/', payload={},
                                    expected_status=200, check_payload=False)
        executions = [execution['id'] for execution in instance['executions']]
        self.assertFalse(id in executions)


class TestExecutionsDataEndpoint(TestExecutionsDetailEndpointMock):

    def setUp(self):
        super().setUp()
        self.response_items = {'id', 'name', 'data'}
        self.items_to_check = ['name']

    def test_get_one_execution(self):
        id = self.create_new_row('/execution/?run=0', self.model, self.payload)
        self.url = '/execution/' + id + '/data/'
        payload = dict(self.payload)
        payload['id'] = id
        self.get_one_row(self.url, payload)


class TestExecutionsLogEndpoint(TestExecutionsDetailEndpointMock):

    def setUp(self):
        super().setUp()
        self.response_items = {'id', 'name', 'log'}
        self.items_to_check = ['name']

    def test_get_one_execution(self):
        id = self.create_new_row('/execution/?run=0', self.model, self.payload)
        payload = dict(self.payload)
        payload['id'] = id
        self.get_one_row('/execution/' + id + '/log/', payload)


class TestExecutionsModel(CustomTestCase):

    def setUp(self):
        super().setUp()

    # TODO: should these tests be implemented? The functions that these tests should cover are already covered
    #  by other test cases, mainly the endpoint functions that use this functions
    def test_save(self):
        pass

    def test_update(self):
        pass

    def test_disable(self):
        pass

    def test_delete(self):
        pass

    def test_get_all_executions(self):
        pass

    def test_get_one_execution_from_id(self):
        pass

    def test_get_one_execution_from_user(self):
        pass

    def test_get_execution_with_reference(self):
        pass

    def test_get_execution_data(self):
        pass

    def test_repr_method(self):
        pass

    def test_str_method(self):
        pass