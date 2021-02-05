import json
import pulp
import logging as log
import time

from cornflow.shared.utils import db
from cornflow.tests.custom_liveServer import CustomTestCaseLive
from cornflow.models import UserModel


class TestCornflowClient(CustomTestCaseLive):

    # TODO:
    #  user management
    #  get status?
    # TODO: test joining urls with url_join goes bad
    # TODO: infeasible execution

    def setUp(self, create_all=False):
        super().setUp()
        self.items_to_check = ['name', 'description']

    def create_new_instance_file(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        response = self.client.\
            create_instance_file(filename=mps_file,
                                 name=name,
                                 description=description,
                                 minimize=True)
        self.assertTrue('id' in response)
        instance = self.client.get_one_instance(response['id'])
        log.debug('Got instance with id: {}'.format(instance['id']))
        # row = InstanceModel.query.get(response['id'])
        self.assertEqual(instance['id'], response['id'])
        self.assertEqual(instance['name'], name)
        self.assertEqual(instance['description'], description)
        payload = pulp.LpProblem.fromMPS(mps_file, sense=1)[1].toDict()
        instance_data = self.client.get_api_for_id('instance', response['id'], 'data').json()
        self.assertEqual(instance_data['data'], payload)
        log.debug('validated instance data')
        return instance

    def create_new_instance(self, mps_file):
        name = 'test_instance1'
        description = 'description123'
        data = pulp.LpProblem.fromMPS(mps_file, sense=1)[1].toDict()
        response = self.client.\
            create_instance(data=data, name=name, description=description)
        log.debug('Created instance with id: {}'.format(response['id']))
        self.assertTrue('id' in response)
        instance = self.client.get_one_instance(response['id'])
        log.debug('Instance with id={} exists in server'.format(instance['id']))
        self.assertEqual(instance['id'], response['id'])
        self.assertEqual(instance['name'], name)
        self.assertEqual(instance['description'], description)
        payload = pulp.LpProblem.fromMPS(mps_file, sense=1)[1].toDict()
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
        return self.create_new_instance('./cornflow/tests/data/test_mps.mps')

    def test_delete_instance(self):
        instance = self.test_new_instance()
        response = self.client.get_api_for_id('instance/', instance['id'])
        self.assertEqual(200, response.status_code)
        response = self.client.delete_api_for_id('instance/', instance['id'])
        self.assertEqual(200, response.status_code)
        response = self.client.get_api_for_id('instance/', instance['id'])
        self.assertEqual(404, response.status_code)

    def test_new_execution(self):
        one_instance = self.create_new_instance('./cornflow/tests/data/test_mps.mps')
        name = "test_execution_name_123"
        description = 'test_execution_description_123'
        payload = dict(instance_id=one_instance['id'],
                       config=dict(solver='PULP_CBC_CMD', timeLimit=10),
                       description=description,
                       name=name)
        return self.create_new_execution(payload)

    def test_delete_execution(self):
        execution = self.test_new_execution()
        response = self.client.get_api_for_id('execution/', execution['id'])
        self.assertEqual(200, response.status_code)
        response = self.client.delete_api_for_id('execution/', execution['id'])
        self.assertEqual(200, response.status_code)
        response = self.client.get_api_for_id('execution/', execution['id'])
        self.assertEqual(404, response.status_code)


class TestCornflowClientAdmin(TestCornflowClient):

    def setUp(self, create_all=False):
        super().setUp()
        user_data = dict(name='airflow_test@admin.com',
                         email='airflow_test@admin.com',
                         password='airflow_test_password')
        # we guarantee that the admin is there for airflow
        self.create_super_admin(user_data)

    def create_super_admin(self, data):
        user = UserModel(data=data)
        user.super_admin = True
        user.save()
        db.session.commit()
        return

    def test_solve_and_wait(self):
        execution = self.test_new_execution()
        time.sleep(15)
        status = self.client.get_status(execution['id'])
        results = self.client.get_results(execution['id'])
        self.assertEqual(status['state'], 1)
        self.assertEqual(results['state'], 1)
