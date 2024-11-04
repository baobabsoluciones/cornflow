"""
Python class to implement the Databricks client wrapper
"""
from databricks.sdk import WorkspaceClient
from flask import current_app
from cornflow_client.orchestrator_constants import config_orchestrator
# TODO AGA: CODIGO REPETIDO
# TODO AGA: revisar si el import está bien
from cornflow_client.constants import DatabricksError

class Databricks:
    def __init__(self, url, token):
        self.client = WorkspaceClient(host=url, token=token)
        self.constants=config_orchestrator["databricks"]

    @classmethod
    def from_config(cls, config):
        data = dict(
            url=config["DATABRICKS_URL"],
            token=config["DATABRICKS_TOKEN"],
        )
        return cls(**data)

    def is_alive(self):
        try:
          # TODO: this url is project specific. Either it has to be a config option or some other way has to be found
          self.client.workspace.get_status(
              path="/Workspace/Repos/nippon/nippon_production_scheduling/main_2.py"
          )
          return True
        except Exception as err:
          current_app.logger.error(f"Error: {err}")
          return False
    
    def get_orch_info(self, orch_name, method="GET"):
        """
        Get information about a job in Databricks
        https://docs.databricks.com/api/workspace/jobs/get
        """
        # TODO AGA: decidir si incluir las url de documentacion en el código
        # TODO AGA: revisar si la url esta bien/ si acepta asi los parámetros
        url = f"{self.url}/api/2.1/jobs/get/{orch_name}"
        schema_info = self.request_headers_auth(method=method, url=url) 
        if "error_code" in schema_info.keys():
            raise DatabricksError("JOB not available")
        return schema_info
    # TODO AGA: incluir un id de job por defecto o hacer obligatorio el uso el parámetro. 
    #   Revisar los efectos secundarios de eliminar execution_id y usar el predeterminado
    def run_workflow(
            self, execution_id, orch_name=config_orchestrator["def_schema"], checks_only=False, case_id=None
        ):
        """
        Run a job in Databricks
        """
        # TODO AGA: revisar si la url esta bien/si acepta asi los parámetros
        url = f"{self.url}/api/2.1/jobs/run-now/"
        # TODO AGA: revisar si deben ser notebook parameters o job parameters. 
        #   Entender cómo se usa checks_only
        payload = dict(job_id=orch_name, notebook_parameters=dict(checks_only=checks_only))
        return self.request_headers_auth(method="POST", url=url, json=payload)
    
    def get_run_status(self, workflow_name, run_id):
        """
        Get the status of a run in Databricks
        """
        url = f"{self.url}/api/2.1/jobs/runs/get"
        payload = dict(run_id=run_id)
        info = self.request_headers_auth(method="POST", url=url, json=payload)
        info = info.json()
        state = info["status"]
        return state