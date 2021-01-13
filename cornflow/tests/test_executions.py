from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
EXECUTION_PATH = './cornflow/tests/data/new_execution.json'
EXECUTIONS_LIST = [EXECUTION_PATH, './cornflow/tests/data/new_execution_2.json']


class TestExecutionsListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()

        self.url = '/instance/'
        self.model = InstanceModel
        fk_id = self.create_new_row(INSTANCE_PATH)
        self.foreign_keys = {'instance_id': fk_id}

        self.url = '/execution/'
        self.model = ExecutionModel

    def test_new_execution(self):
        self.create_new_row(EXECUTION_PATH)

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

        self.url = '/execution/'
        self.model = ExecutionModel

        self.id = self.create_new_row(EXECUTION_PATH)
        self.url = self.url + self.id + '/'

    def test_get_one_execution(self):
        self.get_one_row(EXECUTION_PATH)

    def test_update_one_execution(self):
        pass

    def test_delete_one_execution(self):
        self.delete_row()


class TestExecutionsModel(CustomTestCase):

    def setUp(self):
        super().setUp()

    # TODO: should these test be implemented? The funtions that these test should cover are already covered
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