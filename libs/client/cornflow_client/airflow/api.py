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
from cornflow_client.airflow.dag_utilities import get_workflow_name_check_kpis
from cornflow_client.constants import AirflowError, config_orchestrator


class Airflow(object):
    def __init__(self, url, user, pwd):
        self.base_url = url
        self.url = f"{url}/api/v1"
        self.user = user
        self.pwd = pwd
        self.auth = HTTPBasicAuth(user, pwd)
        self.constants = config_orchestrator["airflow"]
        # Airflow 3 replaced /api/v1 (basic auth) with /api/v2 (JWT bearer auth).
        # The version is auto-detected on first call and cached on the instance
        # so the same client works against Airflow 2 and Airflow 3 clusters.
        self._api_version = None
        self._jwt_token = None

    @property
    def api_url(self):
        return f"{self.base_url}/api/{self._resolve_api_version()}"

    def _resolve_api_version(self):
        if self._api_version is None:
            self.is_alive()
            if self._api_version is None:
                # couldn't reach Airflow at all; default to v1 and let the
                # actual request fail with a meaningful connection error
                self._api_version = "v1"
        return self._api_version

    def _get_jwt_token(self):
        if self._jwt_token is None:
            response = requests.post(
                f"{self.base_url}/auth/token",
                json={"username": self.user, "password": self.pwd},
            )
            if response.status_code >= 300:
                raise AirflowError(
                    error=response.text, status_code=response.status_code
                )
            self._jwt_token = response.json()["access_token"]
        return self._jwt_token

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

        Airflow 3 removed the v1 health endpoint (/api/v1/health) in favour
        of /api/v2/monitor/health. If the v1 endpoint answers 404, retry
        against the v2 endpoint so this works against both Airflow 2 and 3.
        As a side effect, this caches which API version (v1 or v2) is used
        for every other call made through this instance.

        :param config: The configuration dictionary
        :return: True if the Airflow server is alive, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/v1/health")
            if response.status_code == 404:
                self._api_version = "v2"
                response = requests.get(f"{self.base_url}/api/v2/monitor/health")
            else:
                self._api_version = "v1"
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

        Airflow 2 (v1) authenticates with HTTP Basic Auth; Airflow 3 (v2)
        requires a JWT bearer token instead. If a cached token has expired
        (401), it is refreshed once and the request retried.

        :param status: The status code to check
        :param kwargs: The keyword arguments to pass to the request
        :return: The response
        """
        def_headers = {"Content-type": "application/json", "Accept": "application/json"}
        headers = kwargs.pop("headers", def_headers)
        if self._resolve_api_version() == "v2":
            headers = {**headers, "Authorization": f"Bearer {self._get_jwt_token()}"}
            response = requests.request(headers=headers, **kwargs)
            if response.status_code == 401:
                self._jwt_token = None
                headers["Authorization"] = f"Bearer {self._get_jwt_token()}"
                response = requests.request(headers=headers, **kwargs)
        else:
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
        url = f"{self.api_url}/dags/{dag_name}/dagRuns"
        if dag_run_id is not None:
            url = url + f"/{dag_run_id}"
        elif method == "POST" and self._resolve_api_version() == "v2":
            # Airflow 3's trigger endpoint requires the "logical_date" key to
            # be present (null lets Airflow auto-assign it, same as omitting
            # "execution_date" used to do on Airflow 2's v1 endpoint).
            payload = dict(payload or {})
            payload.setdefault("logical_date", None)
        response = self.request_headers_auth(method=method, url=url, json=payload)
        return response

    def set_dag_run_state(self, dag_name, payload):
        """
        Set the state of a DAG run.

        DEPRECATION: only valid against Airflow 2 (v1). Airflow 3 (v2)
        removed this endpoint; use set_dag_run_to_fail() instead, which
        picks the right call for the detected API version.

        :param dag_name: The name of the DAG
        :param payload: The payload to pass to the request
        :return: The response
        """
        url = f"{self.api_url}/dags/{dag_name}/updateTaskInstancesState"
        return self.request_headers_auth(method="POST", url=url, json=payload)

    def run_workflow(
        self,
        execution_id,
        workflow_name=config_orchestrator["airflow"]["def_schema"],
        checks_only=None,
        checks_and_kpis_only=False,
        case_id=None,
    ):
        """
        Run a workflow.

        :param execution_id: The ID of the execution
        :param workflow_name: The name of the DAG
        :param checks_and_kpis_only: Whether to run the checks and KPIs only
        :param case_id: The ID of the case
        :return: The response
        """
        if checks_only is not None:
            warnings.warn(
                "The parameter checks_only is deprecated and will be removed in future versions. "
                "Please use 'checks_and_kpis_only' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            checks_and_kpis_only = checks_only

        conf = dict(exec_id=execution_id, checks_and_kpis_only=checks_and_kpis_only)
        if checks_and_kpis_only:
            workflow_name = get_workflow_name_check_kpis(workflow_name)
        if case_id is not None:
            conf["case_id"] = case_id
        payload = dict(conf=conf)
        return self.consume_dag_run(workflow_name, payload=payload, method="POST")

    def run_dag(
        self,
        execution_id,
        dag_name="solve_model_dag",
        checks_only=None,
        checks_and_kpis_only=False,
        case_id=None,
    ):
        """
        Run workflow.

        DEPRECATION: This method is deprecated and will be removed in version 2.0.0.

        :param execution_id: The ID of the execution
        :param dag_name: The name of the DAG
        :param checks_only: Whether to run the checks only. Deprecated.
        :param checks_and_kpis_only: Whether to run the checks and KPIs only
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
            checks_and_kpis_only=checks_and_kpis_only,
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

    def get_run_status(self, schema, run_id, checks_and_kpis_workflow=False):
        """
        Get the status of a DAG run.

        :param schema: The name of the DAG
        :param run_id: The ID of the DAG run
        :param checks_and_kpis_workflow: Whether to run the checks and KPIs DAG
        :return: The status of the DAG run
        """
        if checks_and_kpis_workflow:
            schema = get_workflow_name_check_kpis(schema)
        return self.consume_dag_run(
            schema, payload=None, dag_run_id=run_id, method="GET"
        )

    def get_dag_run_status(self, dag_name, dag_run_id, checks_and_kpis_workflow=False):
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
        return self.get_run_status(dag_name, dag_run_id, checks_and_kpis_workflow)

    def set_dag_run_to_fail(
        self, dag_name, run_id, new_status="failed", checks_and_kpis_workflow=False
    ):
        """
        Set the status of a DAG run to failed.

        :param dag_name: The name of the DAG
        :param run_id: The ID of the DAG run
        :param new_status: The new status of the DAG run
        :return: The response
        """
        if checks_and_kpis_workflow:
            dag_name = get_workflow_name_check_kpis(dag_name)

        # TODO: We assume the solving task is named as is parent dag!
        if self._resolve_api_version() == "v2":
            # Airflow 3 replaced updateTaskInstancesState with a per-task
            # PATCH; the dag_run_id is already part of the URL, so there's
            # no need for a first call to fetch the run's execution date.
            # PatchTaskInstanceBody forbids extra fields and has no "dry_run"
            # or "task_id" field (dry-run is a separate endpoint in v2).
            url = (
                f"{self.api_url}/dags/{dag_name}/dagRuns/{run_id}"
                f"/taskInstances/{dag_name}"
            )
            payload = dict(
                include_downstream=True,
                include_future=False,
                include_past=False,
                include_upstream=True,
                new_state=new_status,
            )
            return self.request_headers_auth(method="PATCH", url=url, json=payload)

        # here, two calls have to be done:
        # first we get information on the dag_run
        dag_run = self.consume_dag_run(
            dag_name, payload=None, dag_run_id=run_id, method="GET"
        )
        dag_run_data = dag_run.json()
        # then, we use the "executed_date" to build a call to the change state api
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

    def get_all_dag_runs(self, dag_name, checks_and_kpis_workflow=False):
        """
        Get all the DAG runs.

        :param dag_name: The name of the DAG
        :param checks_and_kpis_workflow: Whether to run the checks and KPIs DAG
        :return: The response
        """
        if checks_and_kpis_workflow:
            dag_name = get_workflow_name_check_kpis(dag_name)
        return self.consume_dag_run(dag_name=dag_name, payload=None, method="GET")

    def get_workflow_info(
        self, workflow_name, method="GET", checks_and_kpis_workflow=False
    ):
        """
        Get the information of a DAG.

        :param workflow_name: The name of the DAG
        :param method: The method to use to get the information
        :param checks_and_kpis_workflow: Whether to get the information of the checks and KPIs DAG
        :return: The information of the DAG
        """
        if checks_and_kpis_workflow:
            workflow_name = get_workflow_name_check_kpis(workflow_name)
        # TODO: cleanup method input arguments
        url = f"{self.api_url}/dags/{workflow_name}"
        schema_info = self.request_headers_auth(method=method, url=url)
        if schema_info.status_code != 200:
            raise AirflowError("DAG not available")
        return schema_info

    def get_dag_info(self, dag_name, method="GET", checks_and_kpis_workflow=False):
        """
        Get the information of a DAG.

        DEPRECATION: This method is deprecated and will be removed in version 2.0.0.

        :param dag_name: The name of the DAG
        :param method: The method to use to get the information
        :param checks_and_kpis_workflow: Whether to get the information of the checks and KPIs DAG
        :return: The information of the DAG
        """
        warnings.warn(
            "This method is deprecated and will be removed in version 2.0.0. "
            "Please use get_workflow_info() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_workflow_info(dag_name, method, checks_and_kpis_workflow)

    def get_one_variable(self, variable):
        """
        Get one variable.

        :param variable: The name of the variable
        :return: The variable
        """
        url = f"{self.api_url}/variables/{variable}"
        return self.request_headers_auth(method="GET", url=url).json()

    def get_all_variables(self):
        """
        Get all variables.

        :return: The variables
        """
        return self.request_headers_auth(
            method="GET", url=f"{self.api_url}/variables"
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
        url = f"{self.api_url}/dags"
        return self.request_headers_auth(method=method, url=url)

    def get_internal_dags(self, method="GET"):
        """
        Get all internal DAGs.

        :param method: The method to use to get the DAGs
        :return: The DAGs
        """
        url = f"{self.api_url}/dags?tags=internal"
        return self.request_headers_auth(method=method, url=url)

    def get_model_dags(self, method="GET"):
        """
        Get all model DAGs.

        :param method: The method to use to get the DAGs
        :return: The DAGs
        """
        url = f"{self.api_url}/dags?tags=model"
        return self.request_headers_auth(method=method, url=url)
