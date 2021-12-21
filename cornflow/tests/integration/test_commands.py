from cornflow.tests.custom_liveServer import CustomTestCaseLive
from flask import current_app
from cornflow.models import DeployedDAG
from cornflow.commands.dag import register_deployed_dags_command


class TestCornflowCommands(CustomTestCaseLive):
    def setUp(self, create_all=False):
        super().setUp()

    def test_dag_command(self):
        config = current_app.config
        register_deployed_dags_command(
            config["AIRFLOW_URL"], config["AIRFLOW_USER"], config["AIRFLOW_PWD"], 0
        )
        dags = DeployedDAG.get_all_objects()
        for dag in ["solve_model_dag", "gc", "timer"]:
            self.assertIn(dag, [d.id for d in dags])
