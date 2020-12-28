import json

from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase


class TestInstances(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instance/'
        self.model = InstanceModel
        with open('./cornflow/tests/data/new_instance.json') as f:
            self.payload = json.load(f)

    def test_new_instance(self):
        self.create_new_row()
