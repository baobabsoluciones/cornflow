from cornflow.models import InstanceModel, ExecutionModel
from cornflow.tests.custom_liveServer import CustomTestCaseLive
import pulp
import time


class TestInstances(CustomTestCaseLive):

    # TODO:
    #  delete instance, new / delete execution, user management
    #  get status?

    def create_new_instance_file(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        response = self.client.create_instance_file(filename=mps_file,
                                                       name=name,
                                                       description=description)
        self.assertTrue('id' in response)
        row = InstanceModel.query.get(response['id'])
        self.assertEqual(row.id, response['id'])
        self.assertEqual(row.name, name)
        self.assertEqual(row.description, description)
        payload = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        self.assertEqual(row.data, payload)
        return row

    def create_new_instance(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        data = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        response = self.client.create_instance(data=data,
                                               name=name,
                                               description=description)
        self.assertTrue('id' in response)
        row = InstanceModel.query.get(response['id'])
        self.assertEqual(row.id, response['id'])
        self.assertEqual(row.name, name)
        self.assertEqual(row.description, description)
        payload = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        self.assertEqual(row.data, payload)
        return row

    def create_new_execution(self, instance_id, config):
        name = "test_execution_name_123"
        description = 'test_execution_description_123'
        response = self.client.create_execution(instance_id=instance_id,
                                     config=config,
                                     description=description,
                                     name=name)
        self.assertTrue('id' in response)
        row = ExecutionModel.query.get(response['id'])
        self.assertEqual(row.id, response['id'])
        self.assertEqual(row.name, name)
        self.assertEqual(row.description, description)
        time.sleep(5)
        response = self.client.get_status(response['id'])
        self.assertTrue('status' in response)
        return row

    def test_new_instance_file(self):
        self.create_new_instance_file('./cornflow/tests/data/test_mps.mps')

    def test_new_instance(self):
        self.create_new_instance('./cornflow/tests/data/test_mps.mps')

    def test_new_execution(self):
        one_instance = self.create_new_instance('./cornflow/tests/data/test_mps.mps')
        self.create_new_execution(one_instance.id, config=dict(solver='PULP_CBC_CMD', timeLimit=10))
