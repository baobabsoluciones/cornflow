"""
Python class to implement the Pulse client wrapper.

Pulse runs every execution as a Kubernetes Job. Each launch of a cornflow
execution (first run or relaunch) gets its own run id, returned by Pulse as
"run_id", which cornflow stores in the execution like an Airflow dag run id.
"""

# Full imports
import logging
import warnings

import requests

# Imports from modules
from cornflow_client.constants import config_orchestrator, PulseError

log = logging.getLogger(__name__)

# Seconds to wait for Pulse before giving up on a request
DEFAULT_TIMEOUT = 30


class Pulse:
    def __init__(self, url, token=None, timeout=DEFAULT_TIMEOUT):
        """
        :param str url: base URL of the Pulse API (without the /pulse prefix)
        :param str token: optional shared token sent as a Bearer token
        :param int timeout: seconds to wait for each request
        """
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.constants = config_orchestrator["pulse"]

    @classmethod
    def from_config(cls, config):
        return cls(
            url=config["PULSE_URL"],
            token=config.get("PULSE_TOKEN"),
            timeout=int(config.get("PULSE_TIMEOUT") or DEFAULT_TIMEOUT),
        )

    def is_alive(self, config=None):
        """
        Checks that Pulse answers its health endpoint and reports itself healthy
        (database and Kubernetes API reachable).

        :param dict config: for compatibility with the other orchestrator clients
        """
        try:
            response = self.request_headers_auth(
                method="GET", url=f"{self.url}/pulse/health"
            )
            return response.json().get("status") == "healthy"
        except Exception as err:
            log.error(f"Error checking Pulse health: {err}")
            return False

    def get_workflow_info(self, workflow_name, method="GET", **kwargs):
        """
        Get information about a workflow (cornflow DAG) in Pulse.

        :param str workflow_name: name of the workflow (the execution schema)
        :param str method: the HTTP method to use for the request
        :param dict kwargs: for compatibility with the airflow API
        """
        url = f"{self.url}/pulse/workflows/{workflow_name}"
        try:
            return self.request_headers_auth(method=method, url=url)
        except PulseError as err:
            raise PulseError(
                f"Workflow {workflow_name} not available in Pulse: {err}",
                status_code=err.status_code,
            )

    def run_workflow(
        self,
        execution_id,
        workflow_name=config_orchestrator["pulse"]["def_schema"],
        checks_only=None,
        checks_and_kpis_only=False,
        case_id=None,
    ):
        """
        Launches an execution in Pulse (creates its Kubernetes Job).
        The response contains the "run_id" of this launch.

        :param str execution_id: id of the cornflow execution
        :param str workflow_name: name of the workflow (the execution schema)
        :param bool checks_only: deprecated, use checks_and_kpis_only
        :param bool checks_and_kpis_only: only compute checks and kpis, do not solve
        :param case_id: case whose checks and kpis are computed
        """
        if checks_only is not None:
            warnings.warn(
                "The parameter checks_only is deprecated and will be removed in future versions. "
                "Please use 'checks_and_kpis_only' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            checks_and_kpis_only = checks_only

        payload = dict(
            schema_id=workflow_name,
            cornflow_execution_id=execution_id,
            checks_and_kpis_only=checks_and_kpis_only,
            case_id=case_id,
        )
        return self.request_headers_auth(
            method="POST", url=f"{self.url}/pulse/instances", json=payload, status=201
        )

    def get_run_status(self, schema, run_id, **kwargs):
        """
        Get the status of a launch in Pulse: queued, processing, completed,
        failed or stopped.

        :param str schema: the schema of the execution
        :param str run_id: the run id returned by run_workflow
        :param dict kwargs: for compatibility with the airflow API
        """
        response = self.request_headers_auth(
            method="GET", url=f"{self.url}/pulse/instances/{run_id}"
        )
        return response.json().get("status")

    def request_headers_auth(self, status=200, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = requests.request(headers=headers, **kwargs)
        except requests.exceptions.RequestException as err:
            raise PulseError(f"Pulse is not reachable: {err}", status_code=400)
        if status is None:
            return response
        if response.status_code != status:
            raise PulseError(error=response.text, status_code=response.status_code)
        return response
