from flask import current_app

from cornflow.commands.dag import register_deployed_dags_command
from cornflow.models import DeployedDAG
from cornflow.tests.const import PUBLIC_DAGS
from cornflow.tests.custom_liveServer import CustomTestCaseLive


class TestCornflowCommands(CustomTestCaseLive):
    def setUp(self, create_all=True):
        super().setUp()

    def test_dag_command(self):
        config = current_app.config
        register_deployed_dags_command(
            config["AIRFLOW_URL"], config["AIRFLOW_USER"], config["AIRFLOW_PWD"], False
        )
        dags = DeployedDAG.get_all_objects()

        for dag in PUBLIC_DAGS:
            self.assertIn(dag, [d.id for d in dags])
