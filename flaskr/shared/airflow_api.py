import requests
import json
from urllib.parse import urljoin


class Airflow(object):

    # TODO: get_status
    # TODO: user_authentication

    def __init__(self, url):
        self.url = url

    def run_dag(self, execution_id, cornflow_url):
        conf = dict(exec_id=execution_id,
                    cornflow_url=cornflow_url)
        return requests.post(
            urljoin(self.url, '/api/experimental/dags/solve_model_dag/dag_runs'),
            json={"conf": json.dumps(conf)})
