"""
Python class to implement the Databricks client wrapper
"""

from databricks.sdk import WorkspaceClient
from flask import current_app


class Databricks:
    def __init__(self, url, token):
        self.client = WorkspaceClient(host=url, token=token)

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
        # TODO AGA: revisar si la url esta bien/ si acepta asi los parámetros
        url = f"{self.url}/api/2.1/jobs/get/{orch_name}"
        schema_info = self.request_headers_auth(method=method, url=url) 
        list_all_jobs_id = [job["job_id"] for job in list_all_jobs_info["jobs"]]
        if "error_code" in schema_info.keys():
            raise DatabricksError("JOB not available")
        return schema_info
    # TODO AGA: incluir un id de job por defecto o hacer obligatorio el uso el parámetro. 
    #   Revisar los efectos secundarios de eliminar execution_id y usar el predeterminado
    def run_workflow(
            self, execution_id, dag_name="solve_model_dag", checks_only=False, case_id=None
        ):
        # TODO AGA: revisar si la url esta bien/si acepta asi los parámetros
        # TODO AGA: cambiar los nombres para que sean genéricos
        url = f"{self.url}/api/2.1/jobs/run-now/"
        run_id = self.request_headers_auth(method=method, url=url)
        # TODO AGA: revisar si deben ser notebook parameters o job parameters. 
        #   Entender cómo se usa checks_only
        payload = dict(job_id=dag_name, notebook_parameters=dict(checks_only=checks_only))
        return self.request_headers_auth(method="POST", url=url, json=payload)
