"""
This module contains the Airflow class, which is used to interact with the Airflow API.

The Airflow class is used to:
- Check if the Airflow server is alive
- Request headers with authentication
- Consume a DAG run
- Set the state of a DAG run
- Run a workflow
"""

# Full imports
import json
import requests
import warnings

# Partial imports
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, HTTPError

# Imports from modules
from cornflow_client.constants import AirflowError
from cornflow_client.constants import config_orchestrator


class Airflow(object):
    def __init__(self, url, user, pwd):
        self.url = f"{url}/api/v1"
        self.auth = HTTPBasicAuth(user, pwd)
        self.constants = config_orchestrator["airflow"]

    @classmethod
    def from_config(cls, config):
        """
        Create an Airflow client from a configuration dictionary.

        :param config: The configuration dictionary
        :return: The Airflow client
        """
        data = dict(
            url=config["AIRFLOW_URL"],
            user=config["AIRFLOW_USER"],
            pwd=config["AIRFLOW_PWD"],
        )
        return cls(**data)

    def is_alive(self, config=None):
        """
        Check if the Airflow server is alive.

        :param config: The configuration dictionary
        :return: True if the Airflow server is alive, False otherwise
        """
        try:
            response = requests.get(f"{self.url}/health")
        except (ConnectionError, HTTPError):
            return False
        try:
            data = response.json()
            database = data["metadatabase"]["status"] == "healthy"
            scheduler = data["scheduler"]["status"] == "healthy"
        except json.JSONDecodeError:
            return False
        except KeyError:
            return False

        return database and scheduler

    def request_headers_auth(self, status=200, **kwargs):
        """
        Request headers with authentication.

        :param status: The status code to check
        :param kwargs: The keyword arguments to pass to the request
        :return: The response
        """
        def_headers = {"Content-type": "application/json", "Accept": "application/json"}
        headers = kwargs.get("headers", def_headers)
        response = requests.request(headers=headers, auth=self.auth, **kwargs)
        if response.status_code != status:
            raise AirflowError(error=response.text, status_code=response.status_code)
        return response

    def consume_dag_run(self, dag_name, payload, dag_run_id=None, method="POST"):
        """
        Consume a DAG run.

        :param dag_name: The name of the DAG
        :param payload: The payload to pass to the request
        :param dag_run_id: The ID of the DAG run
        :param method: The method to use to consume the DAG run
        :return: The response
        """
        # TODO: cleanup method input arguments
        url = f"{self.url}/dags/{dag_name}/dagRuns"
        if dag_run_id is not None:
            url = url + f"/{dag_run_id}"
        response = self.request_headers_auth(method=method, url=url, json=payload)
        return response

    def set_dag_run_state(self, dag_name, payload):
        """
        Set the state of a DAG run.

        :param dag_name: The name of the DAG
        :param payload: The payload to pass to the request
        :return: The response
        """
        url = f"{self.url}/dags/{dag_name}/updateTaskInstancesState"
        return self.request_headers_auth(method="POST", url=url, json=payload)

    def run_workflow(
        self,
        execution_id,
        workflow_name=config_orchestrator["airflow"]["def_schema"],
        checks_only=False,
        case_id=None,
    ):
        """
        Run a workflow.

        :param execution_id: The ID of the execution
        :param workflow_name: The name of the DAG
        :param checks_only: Whether to run the checks only
        :param case_id: The ID of the case
        :return: The response
        """
        conf = dict(exec_id=execution_id, checks_only=checks_only)
        if case_id is not None:
            conf["case_id"] = case_id
        payload = dict(conf=conf)
        return self.consume_dag_run(workflow_name, payload=payload, method="POST")

    def run_dag(
        self, execution_id, dag_name="solve_model_dag", checks_only=False, case_id=None
    ):
        """
        Run workflow.

        DEPRECATION: This method is deprecated and will be removed in version 2.0.0.

        :param execution_id: The ID of the execution
        :param dag_name: The name of the DAG
        :param checks_only: Whether to run the checks only
        :param case_id: The ID of the case
        :return: The response
        """
        warnings.warn(
            "This method is deprecated and will be removed in version 2.0.0 "
            "Please use run_workflow() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.run_workflow(
            execution_id,
            workflow_name=dag_name,
            checks_only=checks_only,
            case_id=case_id,
        )

    def update_schemas(self, dag_name="update_all_schemas"):
        """
        Update the schemas.

        :param dag_name: The name of the DAG
        :return: The response
        """
        return self.consume_dag_run(dag_name, payload={}, method="POST")

    def update_dag_registry(self, dag_name="update_dag_registry"):
        """
        Update the DAG registry.

        :param dag_name: The name of the DAG
        :return: The response
        """
        return self.consume_dag_run(dag_name, payload={}, method="POST")

    def get_run_status(self, schema, run_id):
        """
        Get the status of a DAG run.

        :param schema: The name of the DAG
        :param run_id: The ID of the DAG run
        :return: The status of the DAG run
        """
        return self.consume_dag_run(
            schema, payload=None, dag_run_id=run_id, method="GET"
        )

    def get_dag_run_status(self, dag_name, dag_run_id):
        """
        Get the status of a DAG run.

        DEPRECATION: This method is deprecated and will be removed in version 2.0.0.

        :param dag_name: The name of the DAG
        :param dag_run_id: The ID of the DAG run
        :return: The status of the DAG run
        """
        warnings.warn(
            "This method is deprecated and will be removed in version 2.0.0. "
            "Please use get_run_status() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_run_status(dag_name, dag_run_id)

    def set_dag_run_to_fail(self, dag_name, run_id, new_status="failed"):
        """
        Set the status of a DAG run to failed.

        :param dag_name: The name of the DAG
        :param run_id: The ID of the DAG run
        :param new_status: The new status of the DAG run
        :return: The response
        """
        # here, two calls have to be done:
        # first we get information on the dag_run
        dag_run = self.consume_dag_run(
            dag_name, payload=None, dag_run_id=run_id, method="GET"
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
        """
        Get all the DAG runs.

        :param dag_name: The name of the DAG
        :return: The response
        """
        return self.consume_dag_run(dag_name=dag_name, payload=None, method="GET")

    def get_workflow_info(self, workflow_name, method="GET"):
        """
        Get the information of a DAG.

        :param workflow_name: The name of the DAG
        :param method: The method to use to get the information
        :return: The information of the DAG
        """
        # TODO: cleanup method input arguments
        url = f"{self.url}/dags/{workflow_name}"
        schema_info = self.request_headers_auth(method=method, url=url)
        if schema_info.status_code != 200:
            raise AirflowError("DAG not available")
        return schema_info

    def get_dag_info(self, dag_name, method="GET"):
        """
        Get the information of a DAG.

        DEPRECATION: This method is deprecated and will be removed in version 2.0.0.

        :param dag_name: The name of the DAG
        :param method: The method to use to get the information
        :return: The information of the DAG
        """
        warnings.warn(
            "This method is deprecated and will be removed in version 2.0.0. "
            "Please use get_workflow_info() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_workflow_info(dag_name, method)

    def get_one_variable(self, variable):
        """
        Get one variable.

        :param variable: The name of the variable
        :return: The variable
        """
        url = f"{self.url}/variables/{variable}"
        return self.request_headers_auth(method="GET", url=url).json()

    def get_all_variables(self):
        """
        Get all variables.

        :return: The variables
        """
        return self.request_headers_auth(
            method="GET", url=f"{self.url}/variables"
        ).json()

    def get_one_schema(self, dag_name, schema):
        """
        Get one schema.

        :param dag_name: The name of the DAG
        :param schema: The name of the schema
        :return: The schema
        """
        return self.get_schemas_for_dag_name(dag_name)[schema]

    def get_schemas_for_dag_name(self, dag_name):
        """
        Get all schemas for a DAG name.

        :param dag_name: The name of the DAG
        :return: The schemas
        """
        response = self.get_one_variable(dag_name)
        result = json.loads(response["value"])
        result["name"] = response["key"]
        return result

    def get_all_schemas(self):
        """
        Get all schemas.

        :return: The schemas
        """
        response = self.get_all_variables()
        return [dict(name=variable["key"]) for variable in response["variables"]]

    def get_all_dags(self, method="GET"):
        """
        Get all DAGs.

        :param method: The method to use to get the DAGs
        :return: The DAGs
        """
        url = f"{self.url}/dags"
        return self.request_headers_auth(method=method, url=url)

    def get_internal_dags(self, method="GET"):
        """
        Get all internal DAGs.

        :param method: The method to use to get the DAGs
        :return: The DAGs
        """
        url = f"{self.url}/dags?tags=internal"
        return self.request_headers_auth(method=method, url=url)

    def get_model_dags(self, method="GET"):
        """
        Get all model DAGs.

        :param method: The method to use to get the DAGs
        :return: The DAGs
        """
        url = f"{self.url}/dags?tags=model"
        return self.request_headers_auth(method=method, url=url)
