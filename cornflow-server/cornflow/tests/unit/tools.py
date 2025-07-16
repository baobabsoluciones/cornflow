from unittest.mock import Mock, patch
from flask import Flask
import json
import os

from cornflow.shared.const import (
    DATABRICKS_TERMINATE_STATE,
    DATABRICKS_FINISH_TO_STATE_MAP,
)


def create_test_app():
    app = Flask(__name__)
    app.config["CORNFLOW_BACKEND"] = 2
    return app


def patch_af_client(af_client_class):
    with patch("cornflow.endpoints.execution.current_app.config") as mock_config:
        mock_config.__getitem__.side_effect = lambda key: (
            1 if key == "CORNFLOW_BACKEND" else {}
        )
        af_client_mock = Mock()
        responses_mock = Mock()
        responses_mock.json.return_value = {
            "is_paused": False,
            "dag_run_id": "12345",
            "state": "success",
        }
        af_client_mock.is_alive.return_value = True
        af_client_mock.get_workflow_info.return_value = responses_mock

        # Configurar get_workflow_info
        schema_info_mock = Mock()
        schema_info_mock.json.return_value = {"is_paused": False}
        af_client_mock.get_workflow_info.return_value = schema_info_mock

        # Configurar run_workflow
        run_response_mock = Mock()
        run_response_mock.json.return_value = {"dag_run_id": "12345"}
        af_client_mock.run_workflow.return_value = run_response_mock

        # Configurar get_run_status
        status_mock = Mock()
        status_mock.json.return_value = {"state": "success"}
        af_client_mock.get_run_status.return_value = status_mock

        af_client_mock.run_dag.return_value = responses_mock
        af_client_mock.set_dag_run_to_fail.return_value = None
        af_client_class.from_config.return_value = af_client_mock


def patch_db_client(db_client_class):
    mock_config = {"CORNFLOW_BACKEND": 2}

    with patch("cornflow.endpoints.execution.current_app.config", mock_config):
        db_client_mock = Mock()
        responses_mock = Mock()
        responses_mock.json.return_value = {
            "status": {"state": "SUCCESS", "termination_details": {"code": "SUCCESS"}}
        }
        response_run_workflow = Mock()
        response_run_workflow.json.return_value = {
            "run_id": 350148078719367,
            "number_in_job": 350148078719367,
        }
        response_get_workflow_info = Mock()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_data_dir = os.path.join(os.path.dirname(current_dir), "data")
        with open(
            os.path.join(test_data_dir, "patch_databricks_get_orch_info.json")
        ) as f:
            response_get_workflow_info.json.return_value = json.load(f)
        response_get_run_status = Mock()
        with open(
            os.path.join(test_data_dir, "patch_databricks_get_run_status.json")
        ) as f:
            response_get_run_status.json.return_value = json.load(f)
        state = response_get_run_status.json.return_value["status"]["state"]
        if state == DATABRICKS_TERMINATE_STATE:
            if (
                response_get_run_status.json.return_value["status"][
                    "termination_details"
                ]["code"]
                in DATABRICKS_FINISH_TO_STATE_MAP.keys()
            ):
                response_get_run_status = response_get_run_status.json.return_value[
                    "status"
                ]["termination_details"]["code"]
            else:
                response_get_run_status = "OTHER_FINISH_ERROR"
        db_client_mock.is_alive.return_value = True
        db_client_mock.get_workflow_info.return_value = response_get_workflow_info
        db_client_mock.run_workflow.return_value = response_run_workflow
        db_client_mock.get_run_status.return_value = response_get_run_status
        db_client_class.from_config.return_value = db_client_mock
