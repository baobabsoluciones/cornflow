import requests
from requests.exceptions import ConnectionError, HTTPError
from json import JSONDecodeError
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

class Airflow(object):

    def __init__(self, url, user, pwd):
        self.url = url
        self.auth = HTTPBasicAuth(user, pwd)

    def is_alive(self):
        try:
            response = requests.get(self.url + '/health')
        except (ConnectionError, HTTPError):
            return False
        try:
            data = response.json()
        except JSONDecodeError:
            return False
        return data['metadatabase']['status'] == 'healthy' and \
               data['scheduler']['status'] == 'healthy'

    def consume_dag_run(self, dag_name, payload, dag_run_id=None, method='POST'):
        url = urljoin(self.url, '/api/v1/dags/{}/dagRuns'.format(dag_name))
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
            raise AirflowApiError('Airflow responded with a status: {}:\n{}'.
                                  format(response.status_code, response.text))
        return response

    def run_dag(self, execution_id, cornflow_url, dag_name='solve_model_dag'):
        conf = dict(exec_id=execution_id, cornflow_url=cornflow_url)
        payload = dict(conf=conf)
        return self.consume_dag_run(dag_name, payload=payload, method='POST')

    def get_dag_run_status(self, dag_name, dag_run_id):
        return self.consume_dag_run(dag_name, payload=None, dag_run_id=dag_run_id, method='GET')

    def get_all_dag_runs(self, dag_name):
        return self.consume_dag_run(dag_name=dag_name, payload=None, method='GET')


class AirflowApiError(Exception):
    """
    Airflow returns an error
    """
    pass
