"""
Python class to implement the Databricks client wrapper
"""

import requests
import json
from databricks.sdk import WorkspaceClient
from flask import current_app
from cornflow_client.constants import config_orchestrator

from cornflow_client.constants import DatabricksError
from cornflow_client.constants import (
    DATABRICKS_TO_STATE_MAP,
    DATABRICKS_TERMINATE_STATE,
    DATABRICKS_FINISH_TO_STATE_MAP,
)


class Databricks:
    def __init__(self, url, auth_secret, token_endpoint, ep_clusters, client_id):
        self.url = url
        self.constants = config_orchestrator["databricks"]
        self.auth_secret = auth_secret
        self.token_endpoint = token_endpoint
        self.ep_clusters = ep_clusters
        self.client_id = client_id

    @classmethod
    def from_config(cls, config):
        data = dict(
            url=config["DATABRICKS_URL"],
            auth_secret=config["DATABRICKS_AUTH_SECRET"],
            token_endpoint=config["DATABRICKS_TOKEN_ENDPOINT"],
            ep_clusters=config["DATABRICKS_EP_CLUSTERS"],
            client_id=config["DATABRICKS_CLIENT_ID"],
        )
        return cls(**data)

    def get_token(self):
        import requests

        url = f"{self.url}{self.token_endpoint}"
        data = {"grant_type": "client_credentials", "scope": "all-apis"}
        auth = (self.client_id, self.auth_secret)
        oauth_response = requests.post(url, data=data, auth=auth)
        oauth_response.json()
        oauth_token = oauth_response.json()["access_token"]
        return oauth_token

    def is_alive(self, config=None):
        try:
            if config is None or config["DATABRICKS_HEALTH_PATH"] == "default path":
                # We raise an error because the default path is not valid
                raise DatabricksError(
                    "Invalid default path. Please set DATABRICKS_HEALTH_PATH as an environment variable"
                )
            else:
                path = config["DATABRICKS_HEALTH_PATH"]

            url = f"{self.url}/api/2.0/workspace/get-status?path={path}"
            response = self.request_headers_auth(method="GET", url=url)
            if "error_code" in response.json().keys():
                return False
            return True

        except Exception as err:
            current_app.logger.error(f"Error: {err}")
            return False

    def get_workflow_info(self, workflow_name, method="GET"):
        """
        Get information about a job in Databricks
        https://docs.databricks.com/api/workspace/jobs/get
        """
        url = f"{self.url}/api/2.1/jobs/get/?job_id={workflow_name}"
        schema_info = self.request_headers_auth(method=method, url=url)
        if "error_code" in schema_info.json().keys():
            raise DatabricksError("JOB not available")
        return schema_info

    def run_workflow(
        self,
        execution_id,
        workflow_name=config_orchestrator["databricks"]["def_schema"],
        checks_only=False,
        case_id=None,
    ):
        """
        Run a job in Databricks
        """
        url = f"{self.url}/api/2.1/jobs/run-now/"
        #   Entender cómo se usa checks_only
        payload = dict(
            job_id=workflow_name,
            job_parameters=dict(
                checks_only=checks_only,
                execution_id=execution_id,
            ),
        )
        return self.request_headers_auth(method="POST", url=url, json=payload)

    def get_run_status(self, schema, run_id):
        """
        Get the status of a run in Databricks
        """
        print("asking for run id ", run_id)
        url = f"{self.url}/api/2.1/jobs/runs/get"
        payload = dict(run_id=run_id)
        info = self.request_headers_auth(method="GET", url=url, json=payload)
        info = info.json()
        print("info is ", info)
        state = info["status"]["state"]
        if state == DATABRICKS_TERMINATE_STATE:
            if (
                info["status"]["termination_details"]["code"]
                in DATABRICKS_FINISH_TO_STATE_MAP.keys()
            ):
                return info["status"]["termination_details"]["code"]
            else:
                return "OTHER_FINISH_ERROR"
        return state

    def request_headers_auth(self, status=200, **kwargs):
        token = self.get_token()
        def_headers = {"Authorization": "Bearer " + str(token)}
        headers = kwargs.get("headers", def_headers)
        response = requests.request(headers=headers, **kwargs)
        if status is None:
            return response
        if response.status_code != status:
            raise DatabricksError(error=response.text, status_code=response.status_code)
        return response
