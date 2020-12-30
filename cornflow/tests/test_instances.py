from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase


class TestInstances(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel

    def test_new_instance(self):
        self.create_new_row('./cornflow/tests/data/new_instance.json')

    def test_get_instances(self):
        files = ['./cornflow/tests/data/new_instance.json', './cornflow/tests/data/new_instance_2.json']
        self.get_rows(files)

    def test_get_no_instances(self):
        self.get_no_rows()