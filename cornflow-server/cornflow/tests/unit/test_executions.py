"""
Unit test for the executions endpoints
"""

# Import from libraries
from unittest.mock import patch

from cornflow.app import create_app
from cornflow.tests import base_test_execution

# Import from internal modules
from cornflow.tests.const import EXECUTION_URL
from cornflow.tests.unit.tools import patch_af_client, patch_db_client


class TestExecutionsListEndpointAirflow(base_test_execution.BaseExecutionList):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client

    def create_app(self):
        print(
            f"[DEBUG TestExecutionsListEndpointAirflow] Creating app with default config"
        )
        print(
            f"[DEBUG TestExecutionsListEndpointAirflow] Orchestrator target: {self.orchestrator_patch_target}"
        )
        print(
            f"[DEBUG TestExecutionsListEndpointAirflow] Patch function: {self.orchestrator_patch_fn}"
        )
        return super().create_app()


class TestExecutionsListEndpointDatabricks(base_test_execution.BaseExecutionList):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        print(
            f"[DEBUG TestExecutionsListEndpointDatabricks] Creating app with config: testing-databricks"
        )
        print(
            f"[DEBUG TestExecutionsListEndpointDatabricks] Orchestrator target: {self.orchestrator_patch_target}"
        )
        print(
            f"[DEBUG TestExecutionsListEndpointDatabricks] Patch function: {self.orchestrator_patch_fn}"
        )
        app = create_app("testing-databricks")
        return app


class TestExecutionRelaunchEndpointAirflow(base_test_execution.BaseExecutionRelaunch):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionRelaunchEndpointDatabricks(
    base_test_execution.BaseExecutionRelaunch
):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsDetailEndpointAirflow(base_test_execution.BaseExecutionDetail):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionsDetailEndpointDatabricks(base_test_execution.BaseExecutionDetail):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app

    def test_stop_execution(self):
        with patch(self.orchestrator_patch_target) as client:
            self.patch_orchestrator(client)
            idx = self.create_new_row(EXECUTION_URL, self.model, payload=self.payload)

            response = self.client.post(
                self.url + str(idx) + "/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual(
                response.json["message"], "This feature is not available for Databricks"
            )


class TestExecutionsDataEndpointAirflow(base_test_execution.BaseExecutionData):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionsDataEndpointDatabricks(base_test_execution.BaseExecutionData):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsLogEndpointAirflow(base_test_execution.BaseExecutionLog):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionsLogEndpointDatabricks(base_test_execution.BaseExecutionLog):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsModelAirflow(base_test_execution.BaseExecutionModel):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionsModelDatabricks(base_test_execution.BaseExecutionModel):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsStatusEndpointAirflow(base_test_execution.BaseExecutionStatus):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client


class TestExecutionsStatusEndpointDatabricks(base_test_execution.BaseExecutionStatus):
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app
