from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
import json
import pulp


class TestInstances(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.url = '/instancefile/'
        self.model = InstanceModel


    def create_new_row(self, file, name='test1', description=''):
        data = dict(name=name, description=description)
        data['file'] = (open(file, 'rb'), 'test.mps')

        response = self.client.post(self.url,
                                    data=data,
                                    follow_redirects=True,
                                    headers={"Content-Type": "multipart/form-data",
                                             "Authorization": 'Bearer ' + self.token}
                                    )
        self.assertEqual(201, response.status_code)
        row = self.model.query.get(response.json['id'])
        self.assertEqual(row.id, response.json['id'])
        payload = pulp.LpProblem.fromMPS(file)[1].toDict()
        self.assertEqual(row.data, payload)

    def test_new_instance_pyclient(self):
        self.create_new_row('./cornflow/tests/data/test_mps.mps')

    def test_new_instance_fail(self):
        # TODO: bad extension
        # TODO: bad format
        pass
