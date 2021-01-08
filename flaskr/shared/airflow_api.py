import requests
import json
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

class Airflow(object):

    # TODO: get_status for an instance
    # TODO we need an endpoint to check if airflow is alive or not
    # https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/check-health.html

    def __init__(self, url, user, pwd):
        self.url = url
        self.auth = HTTPBasicAuth(user, pwd)

    def is_alive(self):
        response = requests.get(self.url)
        # TODO: complete this!
        return True

    def run_dag(self, execution_id, cornflow_url):
        conf = dict(exec_id=execution_id,
                    cornflow_url=cornflow_url)
        # Content-type: application/json
        # Accept: application/json
        # headers = {'Authorization': 'access_token ' + self.token},
        response = requests.post(
            urljoin(self.url, '/api/v1/dags/solve_model_dag/dagRuns'),
            headers={'Content-type': 'application/json',
                     'Accept': 'application/json'},
            auth=self.auth,
            json={"conf": json.dumps(conf)})
        if response.status_code != 200:
            raise AirflowApiError('Airflow responded with a status: {}:\n{}'.
                                  format(response.status_code, response.text))
        return True



class AirflowApiError(Exception):
    """
    Airflow returns an error
    """
    pass
