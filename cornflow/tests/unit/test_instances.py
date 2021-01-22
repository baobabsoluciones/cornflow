from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
INSTANCES_LIST = [INSTANCE_PATH, './cornflow/tests/data/new_instance_2.json']


class TestInstancesListEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel

    def test_new_instance(self):
        self.create_new_row(INSTANCE_PATH)

    def test_get_instances(self):
        self.get_rows(INSTANCES_LIST)

    def test_get_no_instances(self):
        self.get_no_rows()


class TestInstancesDetailEndpoint(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel
        self.id = self.create_new_row(INSTANCE_PATH)
        self.url = self.url + self.id + '/'

    def test_get_one_instance(self):
        self.get_one_row(INSTANCE_PATH)

    def test_update_one_instance(self):
        self.update_row(INSTANCE_PATH, 'name', 'new_name')

    def test_delete_one_instance(self):
        self.delete_row()


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
