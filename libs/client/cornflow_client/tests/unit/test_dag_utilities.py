import unittest
from cornflow_client.constants import EXECUTION_FILES_STATUS_ERROR
from cornflow_client.raw_cornflow_client import CornFlowApiError
from cornflow_client.airflow import dag_utilities as du
from unittest.mock import Mock, patch


class DagUtilities(unittest.TestCase):
    @patch("cornflow_client.airflow.dag_utilities.CornFlow")
    def test_env_connection_vars(self, CornFlow):
        secrets = Mock()
        conn_uris = [
            (
                "cornflow://some_test_user:very_classified_password@devsm.cornflow.baobabsoluciones.app",
                ("some_test_user", "very_classified_password"),
                "http://devsm.cornflow.baobabsoluciones.app",
            ),
            (
                "https://some_test_user:very_classified_password@devsm.cornflow.baobabsoluciones.app",
                ("some_test_user", "very_classified_password"),
                "https://devsm.cornflow.baobabsoluciones.app",
            ),
            (
                "https://some_test_user:very_classified_password@devsm.cornflow.baobabsoluciones.app/some_dir",
                ("some_test_user", "very_classified_password"),
                "https://devsm.cornflow.baobabsoluciones.app/some_dir",
            ),
            (
                "http://airflow:airflow_test_password@localhost:5000",
                ("airflow", "airflow_test_password"),
                "http://localhost:5000",
            ),
        ]
        client_instance = CornFlow.return_value
        client_instance.login.return_value = ""
        for conn_str, user_info, url in conn_uris:
            secrets.get_conn_value.return_value = conn_str
            du.connect_to_cornflow(secrets)
            client_instance.login.assert_called_with(
                username=user_info[0], pwd=user_info[1]
            )
            CornFlow.assert_called_with(url=url)

    def test_try_to_write_file(self):
        """
        Validates that execution files are written once when the upload succeeds.
        """
        client = Mock()
        payload = {"execution_files_status": 1, "execution_file": Mock()}

        du.try_to_write_file(client, "execution-id", payload)

        client.write_execution_files.assert_called_once_with(
            execution_id="execution-id", **payload
        )

    def test_try_to_write_file_marks_error_when_upload_fails(self):
        """
        Validates that a failed file upload records an execution-files error status.
        """
        client = Mock()
        client.write_execution_files.side_effect = [CornFlowApiError("upload failed"), None]

        with self.assertRaises(du.AirflowDagException):
            du.try_to_write_file(
                client,
                "execution-id",
                {"execution_files_status": 1, "execution_file": Mock()},
            )

        self.assertEqual(2, client.write_execution_files.call_count)
        client.write_execution_files.assert_called_with(
            execution_id="execution-id",
            execution_files_status=EXECUTION_FILES_STATUS_ERROR,
        )

    def test_try_to_write_file_surfaces_fallback_failure(self):
        """
        Validates that fallback upload errors are surfaced to the DAG task.
        """
        client = Mock()
        client.write_execution_files.side_effect = [
            CornFlowApiError("upload failed"),
            CornFlowApiError("fallback failed"),
        ]

        with self.assertRaises(CornFlowApiError):
            du.try_to_write_file(
                client,
                "execution-id",
                {"execution_files_status": 1, "execution_file": Mock()},
            )

        self.assertEqual(2, client.write_execution_files.call_count)
