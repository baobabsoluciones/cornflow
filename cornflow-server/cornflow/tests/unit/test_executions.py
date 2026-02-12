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


class AirflowPatcher:
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Airflow"

    @property
    def orchestrator_patch_fn(self):
        return patch_af_client

    def create_app(self):
        return super().create_app()


class DatabricksPatcher:
    @property
    def orchestrator_patch_target(self):
        return "cornflow.endpoints.execution.Databricks"

    @property
    def orchestrator_patch_fn(self):
        return patch_db_client

    def create_app(self):
        app = create_app("testing-databricks")
        return app


class TestExecutionsListEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionList
):
    pass


class TestExecutionsListEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionList
):
    pass


class TestExecutionRelaunchEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionRelaunch
):
    pass


class TestExecutionRelaunchEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionRelaunch
):
    pass


class TestExecutionsDetailEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionDetail
):
    pass


class TestExecutionsDetailEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionDetail
):
    pass


class TestExecutionsDataEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionData
):
    pass


class TestExecutionsDataEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionData
):
    pass


class TestExecutionsLogEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionLog
):
    pass


class TestExecutionsLogEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionLog
):
    pass


class TestExecutionsModelAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionModel
):
    pass


class TestExecutionsModelDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionModel
):
    pass


class TestExecutionsStatusEndpointAirflow(
    AirflowPatcher, base_test_execution.BaseExecutionStatus
):
    pass


class TestExecutionsStatusEndpointDatabricks(
    DatabricksPatcher, base_test_execution.BaseExecutionStatus
):
    pass
