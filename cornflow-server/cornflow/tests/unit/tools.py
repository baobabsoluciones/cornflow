from unittest.mock import Mock, patch
from flask import Flask


def create_test_app():
    app = Flask(__name__)
    app.config["CORNFLOW_BACKEND"] = 2
    return app


def patch_af_client(af_client_class):
    with patch(
        "cornflow.endpoints.execution_databricks.current_app.config"
    ) as mock_config:
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
        af_client_mock.get_orch_info.return_value = responses_mock
        af_client_mock.run_workflow.return_value = responses_mock
        af_client_mock.get_run_status.return_value = responses_mock
        af_client_mock.set_dag_run_to_fail.return_value = None
        af_client_class.from_config.return_value = af_client_mock


def patch_db_client(db_client_class):
    mock_config = {"CORNFLOW_BACKEND": 2}

    with patch(
        "cornflow.endpoints.execution_databricks.current_app.config", mock_config
    ):
        db_client_mock = Mock()
        responses_mock = Mock()
        responses_mock.json.return_value = {
            "status": {"state": "SUCCESS", "termination_details": {"code": "SUCCESS"}}
        }
        db_client_mock.is_alive.return_value = True
        db_client_mock.get_orch_info.return_value = responses_mock
        db_client_mock.run_workflow.return_value = responses_mock
        db_client_mock.get_run_status.return_value = responses_mock
        db_client_class.from_config.return_value = db_client_mock
