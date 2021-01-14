from cornflow.models import InstanceModel
from cornflow.tests.custom_liveServer import CustomTestCaseLive
import pulp


class TestInstances(CustomTestCaseLive):

    def create_new_instance_file(self, file):
        name = 'test_instance1'
        description = 'description123'
        response = self.client.create_instance_file(filename=file,
                                                       name=name,
                                                       description=description)
        self.assertTrue('id' in response)
        row = InstanceModel.query.get(response['id'])
        self.assertEqual(row.id, response['id'])
        self.assertEqual(row.name, name)
        self.assertEqual(row.description, description)
        payload = pulp.LpProblem.fromMPS(file)[1].toDict()
        self.assertEqual(row.data, payload)

    def test_new_instance(self):
        self.create_new_instance_file('./cornflow/tests/data/test_mps.mps')
