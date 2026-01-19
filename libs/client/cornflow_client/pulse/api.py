import requests
from flask import current_app
from cornflow_client.constants import config_orchestrator, PulseError


class Pulse:
    def __init__(self, url, token=None):
        """
        :param url: URL of the Pulse API
        :param token: Optional authentication token (not used for Pulse)
        """
        self.url = url
        self.token = token
        self.constants = config_orchestrator["pulse"]

    @classmethod
    def from_config(cls, config):
        """
        Creates a Pulse client from the Flask app configuration.
        """
        data = dict(
            url=config["PULSE_URL"],
        )
        return cls(**data)

    def get_token(self):
        """
        Pulse API does not require a token.
        """
        self.token = "not_required"
        return self.token

    def is_alive(self, config=None):
        """
        Checks if the Pulse API is alive.
        """
        
        health_endpoint = "/health"
        try:
            url = f"{self.url}{health_endpoint}"
            response = self.request_headers_auth(method="GET", url=url, status=200)
            # Check if the response body contains a healthy status
            return response.json().get("status") == "healthy"
        except Exception as err:
            current_app.logger.error(f"Error checking Pulse health: {err}")
            return False

    def get_workflow_info(self, workflow_name, method="GET"):
        """
        Get information about a schema in Pulse.
        Corresponds to GET /schemas/<schema_id>
        """
        url = f"{self.url}/schemas/{workflow_name}"
        try:
            response = self.request_headers_auth(method=method, url=url, status=200)
            return response
        except PulseError:
            raise PulseError("Schema (workflow) not available in Pulse")

    def run_workflow(
            self, 
            execution_id, 
            workflow_name=config_orchestrator["pulse"]["def_schema"], 
            checks_only=False, 
            case_id=None
        ):
        """
        Run a job in Pulse by creating a new instance.
        Corresponds to POST /instances
        """
        if checks_only:
            current_app.logger.warning("Pulse client does not support 'checks_only' mode.")
        if case_id:
            current_app.logger.info(f"Pulse client received case_id {case_id}, but it is not currently used.")

        url = f"{self.url}/instances"
        
        payload = dict( 
            schema_id=workflow_name,
            cornflow_execution_id = execution_id,
        )
        current_app.logger.info(f"Pulse payload: {payload}")
        response = self.request_headers_auth(method="POST", url=url, json=payload, status=201)
        return response

    def get_run_status(self, schema, run_id):
        """
        Get the status of a run in Pulse.
        Corresponds to GET /instances/<instance_id>
        """
        try:
            url = f"{self.url}/instances/{run_id}"
            response = self.request_headers_auth(method="GET", url=url, status=200)
            info = response.json()
          
            return info.get("status", "UNKNOWN")
        except PulseError as e:
            if e.status_code == 404:
                return "processing" 
            raise e

    def request_headers_auth(self, status=200, **kwargs):
        """
        Makes a request to the Pulse API. Authentication is not required.
        """
        # No auth headers needed for Pulse now
        headers = kwargs.get("headers", {})
        kwargs.setdefault("headers", headers)

        response = requests.request(**kwargs)

        if status is not None and response.status_code != status:
            raise PulseError(error=response.text, status_code=response.status_code)

        return response
