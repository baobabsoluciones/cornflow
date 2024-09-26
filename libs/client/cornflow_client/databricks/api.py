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
    
