from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
import json


INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
EXECUTION_PATH = './cornflow/tests/data/new_execution.json'
EXECUTIONS_LIST = [EXECUTION_PATH, './cornflow/tests/data/new_execution_2.json']


class TestExecutionsListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()

        self.url = '/instance/'
        self.model = InstanceModel
        # TODO: instead of this, we should create an instance with the models
        fk_id = self.create_new_row(INSTANCE_PATH)
        self.foreign_keys = {'instance_id': fk_id}

        self.url = '/execution/?run=0'
        self.model = ExecutionModel

    def test_new_execution(self):
        self.create_new_row(EXECUTION_PATH)

    def test_new_execution_no_instance(self):
        with open(EXECUTION_PATH) as f:
            payload = json.load(f)

        payload['instance_id'] = 'bad_id'

        response = self.client.post(self.url, data=json.dumps(payload), follow_redirects=True,
                                    headers={"Content-Type": "application/json",
                                             "Authorization": 'Bearer ' + self.token})

        self.assertEqual(400, response.status_code)
        self.assertTrue('error' in response.json)

    def test_get_executions(self):
        self.get_rows(EXECUTIONS_LIST)

    def test_get_no_executions(self):
        self.get_no_rows()


class TestExecutionsDetailEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()

        self.url = '/instance/'
        self.model = InstanceModel
        fk_id = self.create_new_row(INSTANCE_PATH)

        self.foreign_keys = {'instance_id': fk_id}

        self.url = '/execution/?run=0'
        self.model = ExecutionModel

        self.id = self.create_new_row(EXECUTION_PATH)
        self.url = '/execution/' + self.id + '/'
        self.response_items = {'id', 'name', 'description', 'created_at', 'instance_id', 'finished'}
        # we only the following because this endpoint does not return data
        self.items_to_check = ['name', 'description']

    def test_get_one_execution(self):
        self.get_one_row(EXECUTION_PATH)

    def test_update_one_execution(self):
        pass

    def test_delete_one_execution(self):
        self.delete_row()


class TestExecutionsDataEndpoint(TestExecutionsDetailEndpoint):

    def setUp(self):
        super().setUp()
        self.url = '/execution/' + self.id + '/data/'
        self.response_items = {'id', 'name', 'data'}
        self.items_to_check = ['name']

    def test_get_one_execution(self):
        self.get_one_row(EXECUTION_PATH)

    def test_update_one_execution(self):
        pass

    def test_delete_one_execution(self):
        pass

class TestExecutionsLogEndpoint(TestExecutionsDetailEndpoint):

    def setUp(self):
        super().setUp()
        self.url = '/execution/' + self.id + '/log/'
        self.response_items = {'id', 'name', 'log'}
        self.items_to_check = ['name']

    def test_get_one_execution(self):
        self.get_one_row(EXECUTION_PATH)

    def test_update_one_execution(self):
        pass

    def test_delete_one_execution(self):
        pass


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