from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase

INSTANCE_PATH = './cornflow/tests/data/new_instance.json'
INSTANCES_LIST = [INSTANCE_PATH, './cornflow/tests/data/new_instance_2.json']


class TestInstances(CustomTestCase):

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


class TestInstancesDetail(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel
        self.id = self.create_new_row(INSTANCE_PATH)
        self.url = self.url + self.id + '/'

    def test_one_instance(self):
        self.get_one_row(INSTANCE_PATH)
