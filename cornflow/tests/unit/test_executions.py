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

    def test_get_executions_superadmin(self):
        self.get_rows(self.url, self.payloads)
        token = self.create_super_admin()
        rows = self.client.get(self.url, follow_redirects=True,
                               headers=self.get_header_with_auth(token))
        self.assertGreaterEqual(len(rows.json), len(self.payloads))


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

    def test_get_nonexistent_execution(self):
        result = self.get_one_row(self.url + 'some_key_' + '/', {},
                                  expected_status=404, check_payload=False)

    def test_get_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        payload = dict(self.payload)
        payload['id'] = id
        self.get_one_row(self.url + id, payload)

    def test_incomplete_payload(self):
        payload = {'description': 'arg'}
        response = self.create_new_row(self.url + '?run=0', self.model, payload,
                                       expected_status=400, check_payload=False)

    def test_incomplete_payload2(self):
        payload = {'description': 'arg', 'instance_id': self.payload['instance_id']}
        response = self.create_new_row(self.url + '?run=0', self.model, payload,
                                       expected_status=400, check_payload=False)

    def test_payload_bad_format(self):
        payload = {'name': 1}
        response = self.create_new_row(self.url + '?run=0', self.model, payload,
                                       expected_status=400, check_payload=False)

    def test_delete_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        self.delete_row(self.url + id + '/', self.model)
        self.get_one_row(self.url + id, payload={}, expected_status=404, check_payload=False)

    def test_update_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        payload = {**self.payload, **dict(id=id, name='new_name')}
        self.update_row(self.url + id + '/', dict(name='new_name'), payload)

    def test_update_one_execution_bad_format(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        self.update_row(self.url + id + '/', dict(instance_id='some_id'), {},
                        expected_status=400, check_payload=False)

    def test_create_delete_instance_load(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        execution = self.get_one_row(self.url + id, payload={**self.payload, **dict(id=id)})
        self.delete_row(self.url + id + '/', self.model)
        instance = self.get_one_row('/instance/' + execution['instance_id'] + '/', payload={},
                                    expected_status=200, check_payload=False)
        executions = [execution['id'] for execution in instance['executions']]
        self.assertFalse(id in executions)

    def test_delete_instance_deletes_execution(self):
        # we create a new instance
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row('/instance/', InstanceModel, payload)
        payload = {**self.payload, **dict(instance_id=fk_id)}
        # we create an execution for that instance
        id = self.create_new_row(self.url + '?run=0', self.model, payload)
        self.get_one_row(self.url + id, payload={**self.payload, **dict(id=id)})
        # we delete the new instance
        self.delete_row('/instance/' + fk_id + '/', InstanceModel)
        # we check the execution does not exist
        self.get_one_row(self.url + id, payload={}, expected_status=404, check_payload=False)

    def test_get_one_execution_superadmin(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        token = self.create_super_admin()
        self.get_one_row(self.url + id + '/', {**self.payload, **dict(id=id)}, token=token)

    def test_edit_one_execution(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        payload = {**self.payload, **dict(id=id, name='new_name')}
        self.update_row(self.url + id + '/', dict(name='new_name'), payload)


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


class TestExecutionsModel(TestExecutionsDetailEndpointMock):

    def test_repr_method(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        self.repr_method(id, '<id {}>'.format(id))

    def test_str_method(self):
        id = self.create_new_row(self.url + '?run=0', self.model, self.payload)
        self.str_method(id, '<id {}>'.format(id))
