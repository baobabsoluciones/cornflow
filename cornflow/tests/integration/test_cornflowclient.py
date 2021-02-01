from cornflow.tests.custom_liveServer import CustomTestCaseLive
import pulp
import logging as log


class TestInstances(CustomTestCaseLive):

    # TODO:
    #  delete instance, new / delete execution, user management
    #  get status?
    # TODO: test joining urls with url_join goes bad

    def create_new_instance_file(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        response = self.client.create_instance_file(filename=mps_file,
                                                       name=name,
                                                       description=description)
        self.assertTrue('id' in response)
        instance = self.client.get_one_instance(response['id'])
        log.debug('Got instance with id: {}'.format(instance['id']))
        # row = InstanceModel.query.get(response['id'])
        self.assertEqual(instance['id'], response['id'])
        self.assertEqual(instance['name'], name)
        self.assertEqual(instance['description'], description)
        payload = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        instance_data = self.client.get_api_for_id('instance', response['id'], 'data').json()
        self.assertEqual(instance_data['data'], payload)
        log.debug('validated instance data')
        return instance

    def create_new_instance(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        data = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        response = self.client.create_instance(data=data,
                                               name=name,
                                               description=description)
        log.debug('Created instance with id: {}'.format(response['id']))
        self.assertTrue('id' in response)
        instance = self.client.get_one_instance(response['id'])
        log.debug('Instance with id={} exists in server'.format(instance['id']))
        self.assertEqual(instance['id'], response['id'])
        self.assertEqual(instance['name'], name)
        self.assertEqual(instance['description'], description)
        payload = pulp.LpProblem.fromMPS(mps_file)[1].toDict()
        instance_data = self.client.get_api_for_id('instance', response['id'], 'data').json()
        self.assertEqual(instance_data['data'], payload)
        return instance

    def create_new_execution(self, instance_id, config):
        name = "test_execution_name_123"
        description = 'test_execution_description_123'
        response = self.client.create_execution(instance_id=instance_id,
                                     config=config,
                                     description=description,
                                     name=name)
        log.debug('Created execution with id={}'.format(response['id']))
        self.assertTrue('id' in response)
        execution = self.client.get_results(response['id'])
        log.debug('Execution with id={} exists in server'.format(execution['id']))
        self.assertEqual(execution['id'], response['id'])
        self.assertEqual(execution['name'], name)
        self.assertEqual(execution['description'], description)
        response = self.client.get_status(response['id'])
        self.assertTrue('status' in response)
        log.debug('Execution has status={} in server'.format(response['status']))
        return execution

    def test_new_instance_file(self):
        self.create_new_instance_file('./cornflow/tests/data/test_mps.mps')

    def test_new_instance(self):
        self.create_new_instance('./cornflow/tests/data/test_mps.mps')

    def test_new_execution(self):
        one_instance = self.create_new_instance('./cornflow/tests/data/test_mps.mps')
        self.create_new_execution(one_instance['id'], config=dict(solver='PULP_CBC_CMD', timeLimit=10))
