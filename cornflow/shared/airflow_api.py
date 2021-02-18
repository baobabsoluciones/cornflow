import requests
from requests.exceptions import ConnectionError, HTTPError
import json
from requests.auth import HTTPBasicAuth

from ..shared.exceptions import AirflowError, InvalidUsage
from ..schemas.schema_manager import SchemaManager


class Airflow(object):

    def __init__(self, url, user, pwd):
        self.url = url + '/api/v1'
        self.auth = HTTPBasicAuth(user, pwd)

    def is_alive(self):
        try:
            response = requests.get(self.url + '/health')
        except (ConnectionError, HTTPError):
            return False
        try:
            data = response.json()
        except json.JSONDecodeError:
            return False
        return data['metadatabase']['status'] == 'healthy' and \
               data['scheduler']['status'] == 'healthy'

    def consume_dag_run(self, dag_name, payload, dag_run_id=None, method='POST'):
        url = "{}/dags/{}/dagRuns".format(self.url, dag_name)
        if dag_run_id is not None:
            url = url + '/{}'.format(dag_run_id)
        response = requests.request(
            method=method,
            url=url,
            headers={'Content-type': 'application/json',
                     'Accept': 'application/json'},
            auth=self.auth,
            json=payload)
        if response.status_code != 200:
            raise AirflowError(error='Airflow responded with a status: {}:\n{}'.
                               format(response.status_code, response.text))
        return response

    def run_dag(self, execution_id, dag_name='solve_model_dag'):
        conf = dict(exec_id=execution_id)
        payload = dict(conf=conf)
        return self.consume_dag_run(dag_name, payload=payload, method='POST')

    def get_dag_run_status(self, dag_name, dag_run_id):
        return self.consume_dag_run(dag_name, payload=None, dag_run_id=dag_run_id, method='GET')

    def get_all_dag_runs(self, dag_name):
        return self.consume_dag_run(dag_name=dag_name, payload=None, method='GET')

    def get_dag_info(self, dag_name, method='GET'):
        url = "{}/dags/{}".format(self.url, dag_name)
        response = requests.request(
            method=method,
            url=url,
            headers={'Content-type': 'application/json',
                     'Accept': 'application/json'},
            auth=self.auth)
        if response.status_code != 200:
            raise AirflowError(error='Airflow responded with a status: {}:\n{}'.
                               format(response.status_code, response.text))
        return response

    def get_one_variable(self, variable):
        url = "{}/variables/{}".format(self.url, variable)
        response = requests.request(
            method='GET',
            url=url,
            headers={'Content-type': 'application/json',
                     'Accept': 'application/json'},
            auth=self.auth)
        if response.status_code != 200:
            raise AirflowError(error=response.text,
                               status_code=response.status_code)
        return response.json()['value']

    def get_one_schema(self, dag_name, schema):
        return self.get_one_variable("{}_{}".format(dag_name, schema))


    def get_schemas_for_dag_name(self, dag_name):
        return {v: self.get_one_schema(dag_name, v) for v in ['input', 'output']}


def get_schema(config, dag_name, schema='input'):
    airflow_conf = dict(url=config['AIRFLOW_URL'], user=config['AIRFLOW_USER'], pwd=config['AIRFLOW_PWD'])
    af_client = Airflow(**airflow_conf)
    if not af_client.is_alive():
        raise AirflowError(error="Airflow is not accessible")

    schema = af_client.get_one_schema(dag_name, schema)
    schema_json = json.loads(schema)
    manager = SchemaManager(schema_json)
    return manager.jsonschema_to_flask()


def validate_and_continue(obj, data):
    validate = obj.load(data)
    err = ''
    if validate is None:
        raise InvalidUsage(error='Bad data format: {}'.format(err))
    return True
