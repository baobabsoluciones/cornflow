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
    
    def get_orq_info(self, orq_name, method="GET"):
        # TODO AGA: revisar si la url esta bien/ si acepta asi los parámetros
        url = f"{self.url}/api/2.1/jobs/get/{orq_name}"
        schema_info = self.request_headers_auth(method=method, url=url) 
        list_all_jobs_id = [job["job_id"] for job in list_all_jobs_info["jobs"]]
        if "error_code" in schema_info.keys():
            raise DatabricksError("JOB not available")
        return schema_info
        
    def run_workflow(
            self, execution_id, dag_name="solve_model_dag", checks_only=False, case_id=None
        ):
            conf = dict(exec_id=execution_id, checks_only=checks_only)
            if case_id is not None:
                conf["case_id"] = case_id
            payload = dict(conf=conf)
            return self.consume_dag_run(dag_name, payload=payload, method="POST")
        

