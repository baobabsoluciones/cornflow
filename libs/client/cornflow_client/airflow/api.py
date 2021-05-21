import requests
from requests.exceptions import ConnectionError, HTTPError
import json
from requests.auth import HTTPBasicAuth
from cornflow_client import SchemaManager
from marshmallow import ValidationError, INCLUDE

from cornflow_client.constants import AirflowError, InvalidUsage


class Airflow(object):
    def __init__(self, url, user, pwd):
        self.url = url + "/api/v1"
        self.auth = HTTPBasicAuth(user, pwd)

    def is_alive(self):
        try:
            response = requests.get(self.url + "/health")
        except (ConnectionError, HTTPError):
            return False
        try:
            data = response.json()
        except json.JSONDecodeError:
            return False
        return (
            data["metadatabase"]["status"] == "healthy"
            and data["scheduler"]["status"] == "healthy"
        )

    def request_headers_auth(self, status=200, **kwargs):
        def_headers = {"Content-type": "application/json", "Accept": "application/json"}
        headers = kwargs.get("headers", def_headers)
        response = requests.request(headers=headers, auth=self.auth, **kwargs)
        if status is None:
            return response
        if response.status_code != status:
            raise AirflowError(error=response.text, status_code=response.status_code)
        return response

    def consume_dag_run(self, dag_name, payload, dag_run_id=None, method="POST"):
        url = "{}/dags/{}/dagRuns".format(self.url, dag_name)
        if dag_run_id is not None:
            url = url + "/{}".format(dag_run_id)
        response = self.request_headers_auth(method=method, url=url, json=payload)
        return response

    def set_dag_run_state(self, dag_name, payload):
        url = "{}/dags/{}/updateTaskInstancesState".format(self.url, dag_name)
        return self.request_headers_auth(method="POST", url=url, json=payload)

    def run_dag(self, execution_id, dag_name="solve_model_dag"):
        conf = dict(exec_id=execution_id)
        payload = dict(conf=conf)
        return self.consume_dag_run(dag_name, payload=payload, method="POST")

    def get_dag_run_status(self, dag_name, dag_run_id):
        return self.consume_dag_run(
            dag_name, payload=None, dag_run_id=dag_run_id, method="GET"
        )

    def set_dag_run_to_fail(self, dag_name, dag_run_id, new_status="failed"):
        # here, two calls have to be done:
        # first we get information on the dag_run
        dag_run = self.consume_dag_run(
            dag_name, payload=None, dag_run_id=dag_run_id, method="GET"
        )
        dag_run_data = dag_run.json()
        # then, we use the "executed_date" to build a call to the change state api
        # TODO: We assume the solving task is named as is parent dag!
        payload = dict(
            dry_run=False,
            include_downstream=True,
            include_future=False,
            include_past=False,
            include_upstream=True,
            new_state=new_status,
            task_id=dag_name,
            execution_date=dag_run_data["execution_date"],
        )
        return self.set_dag_run_state(dag_name, payload=payload)

    def get_all_dag_runs(self, dag_name):
        return self.consume_dag_run(dag_name=dag_name, payload=None, method="GET")

    def get_dag_info(self, dag_name, method="GET"):
        url = "{}/dags/{}".format(self.url, dag_name)
        return self.request_headers_auth(method=method, url=url)

    def get_one_variable(self, variable):
        url = "{}/variables/{}".format(self.url, variable)
        response = self.request_headers_auth(method="GET", url=url)
        return response.json()["value"]

    def get_one_schema(self, dag_name, schema):
        response = self.get_schemas_for_dag_name(dag_name)
        return response[schema]

    def get_schemas_for_dag_name(self, dag_name):
        return json.loads(self.get_one_variable(dag_name))


def get_schema(config, dag_name, schema="instance"):
    """
    Gets a schema by name from airflow server. We use the variable api.
    We transform the jsonschema into a marshmallow class

    """
    airflow_conf = dict(
        url=config["AIRFLOW_URL"],
        user=config["AIRFLOW_USER"],
        pwd=config["AIRFLOW_PWD"],
    )
    af_client = Airflow(**airflow_conf)
    if not af_client.is_alive():
        raise AirflowError(error="Airflow is not accessible")

    schema_json = af_client.get_one_schema(dag_name, schema)
    manager = SchemaManager(schema_json)
    return manager.jsonschema_to_flask()


def validate_and_continue(obj, data):
    """
    This function validates some data meets a marshmallow object specs.
    In case it does not: we raise an error.
    In case we do, we return the transformed data

    """
    try:
        validate = obj.load(data)
    except ValidationError as e:
        raise InvalidUsage(error="Bad data format: {}".format(e))
    err = ""
    if validate is None:
        raise InvalidUsage(error="Bad data format: {}".format(err))
    return validate
