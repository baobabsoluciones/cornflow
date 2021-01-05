import requests
import json
from urllib.parse import urljoin


class Airflow(object):

    # TODO: get_status for an instance
    # TODO: user_authentication
    # TODO we need an endpoint to check if airflow is alive or not
    # https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/check-health.html

    def __init__(self, url):
        self.url = url

    def is_alive(self):
        response = requests.get(self.url)
        # TODO: complete this!
        return True

    def run_dag(self, execution_id, cornflow_url):
        conf = dict(exec_id=execution_id,
                    cornflow_url=cornflow_url)
        response = requests.post(
            urljoin(self.url, '/api/experimental/dags/solve_model_dag/dag_runs'),
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
