import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch


prev_dir = os.path.join(os.path.dirname(__file__), "../../DAG")
sys.path.insert(0, prev_dir)

# Mock Airflow imports before loading the DAG module.
mymodule = MagicMock()
sys.modules["airflow"] = mymodule
sys.modules["airflow.operators.python"] = mymodule
sys.modules["airflow.secrets.environment_variables"] = mymodule

from cornflow_client import CornFlowApiError
import execution_files_cleanup


class ExecutionFilesCleanupDagTestCase(unittest.TestCase):
    def _client(self):
        client = Mock()
        client.url = "http://cornflow.test"
        client.token = "service-token"
        return client

    def _response(self, status_code=200, payload=None):
        response = Mock(status_code=status_code)
        response.json.return_value = payload or {"message": "Cleanup finished"}
        return response

    @patch.object(execution_files_cleanup, "requests")
    @patch.object(execution_files_cleanup, "connect_to_cornflow")
    @patch.object(execution_files_cleanup, "EnvironmentVariablesBackend")
    def test_cleanup_calls_endpoint_with_auth_header(
        self, environment_backend, connect_to_cornflow, requests
    ):
        """
        Validates that the cleanup DAG calls the execution files cleanup endpoint.
        """
        secrets = Mock()
        client = self._client()
        environment_backend.return_value = secrets
        connect_to_cornflow.return_value = client
        requests.delete.return_value = self._response()

        execution_files_cleanup.execution_files_cleanup()

        connect_to_cornflow.assert_called_once_with(secrets)
        requests.delete.assert_called_once_with(
            "http://cornflow.test/execution/files/cleanup/",
            headers={
                "Authorization": "Bearer service-token",
                "Content-Encoding": "br",
            },
        )

    @patch.object(execution_files_cleanup, "requests")
    @patch.object(execution_files_cleanup, "connect_to_cornflow")
    @patch.object(execution_files_cleanup, "EnvironmentVariablesBackend")
    def test_cleanup_raises_when_delete_fails(
        self, environment_backend, connect_to_cornflow, requests
    ):
        """
        Validates that non-200 cleanup responses raise a CornFlowApiError.
        """
        environment_backend.return_value = Mock()
        connect_to_cornflow.return_value = self._client()
        requests.delete.return_value = self._response(500, {"error": "backend failed"})

        with self.assertRaisesRegex(
            CornFlowApiError, "Could not clean up the execution files"
        ):
            execution_files_cleanup.execution_files_cleanup()

        requests.delete.assert_called_once()

    @patch.object(execution_files_cleanup, "sleep")
    @patch.object(execution_files_cleanup, "requests")
    @patch.object(execution_files_cleanup, "connect_to_cornflow")
    @patch.object(execution_files_cleanup, "EnvironmentVariablesBackend")
    def test_cleanup_retries_login_before_success(
        self, environment_backend, connect_to_cornflow, requests, sleep
    ):
        """
        Validates that login failures are retried before running cleanup.
        """
        environment_backend.return_value = Mock()
        connect_to_cornflow.side_effect = [
            CornFlowApiError("login failed"),
            CornFlowApiError("login failed"),
            self._client(),
        ]
        requests.delete.return_value = self._response()

        execution_files_cleanup.execution_files_cleanup()

        self.assertEqual(3, connect_to_cornflow.call_count)
        self.assertEqual(2, sleep.call_count)
        requests.delete.assert_called_once()

    @patch.object(execution_files_cleanup, "sleep")
    @patch.object(execution_files_cleanup, "requests")
    @patch.object(execution_files_cleanup, "connect_to_cornflow")
    @patch.object(execution_files_cleanup, "EnvironmentVariablesBackend")
    def test_cleanup_raises_after_repeated_login_failures(
        self, environment_backend, connect_to_cornflow, requests, sleep
    ):
        """
        Validates that cleanup fails after the maximum number of login attempts.
        """
        environment_backend.return_value = Mock()
        connect_to_cornflow.side_effect = CornFlowApiError("login failed")

        with self.assertRaisesRegex(CornFlowApiError, "3/3 failed login attempts"):
            execution_files_cleanup.execution_files_cleanup()

        self.assertEqual(3, connect_to_cornflow.call_count)
        self.assertEqual(3, sleep.call_count)
        requests.delete.assert_not_called()
