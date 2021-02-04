from cornflow.tests.custom_liveServer import CustomTestCaseLive
import pulp
import logging as log


class TestCornflowClient(CustomTestCaseLive):

    # TODO:
    #  delete instance, new / delete execution, user management
    #  get status?
    # TODO: test joining urls with url_join goes bad

    def setUp(self, create_all=False):
        super().setUp(False)
        self.items_to_check = ['name', 'description', 'instance_id']

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

    def create_new_execution(self, payload):
        response = self.client.create_execution(**payload)
        log.debug('Created execution with id={}'.format(response['id']))
        self.assertTrue('id' in response)
        execution = self.client.get_results(response['id'])
        log.debug('Execution with id={} exists in server'.format(execution['id']))
        self.assertEqual(execution['id'], response['id'])
        for item in self.items_to_check:
            self.assertEqual(execution[item], payload[item])
        response = self.client.get_status(response['id'])
        self.assertTrue('state' in response)
        log.debug('Execution has state={} in server'.format(response['state']))
        return execution

    def test_new_instance_file(self):
        self.create_new_instance_file('./cornflow/tests/data/test_mps.mps')

    def test_new_instance(self):
        self.create_new_instance('./cornflow/tests/data/test_mps.mps')

    def test_new_execution(self):
        one_instance = self.create_new_instance('./cornflow/tests/data/test_mps.mps')
        name = "test_execution_name_123"
        description = 'test_execution_description_123'
        payload = dict(instance_id=one_instance['id'],
                       config=dict(solver='PULP_CBC_CMD', timeLimit=10),
                       description=description,
                       name=name)

        self.create_new_execution(payload)
