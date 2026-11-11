import os
import tempfile
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

    @patch("cornflow_client.airflow.dag_utilities.CornFlow")
    def test_connection_with_api_key(self, CornFlow):
        # When CORNFLOW_SERVICE_API_KEY is set, the service connection uses
        # the API key and does not log in
        secrets = Mock()
        secrets.get_conn_value.return_value = (
            "cornflow://service_user:pwd@localhost:5000"
        )
        client_instance = CornFlow.return_value
        with patch.dict(os.environ, {"CORNFLOW_SERVICE_API_KEY": "the-api-key"}):
            du.connect_to_cornflow(secrets)
        client_instance.set_api_key.assert_called_with("the-api-key")
        client_instance.login.assert_not_called()

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
        client.write_execution_files.side_effect = [
            CornFlowApiError("upload failed"),
            None,
        ]

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


class DagUtilitiesErrorLog(unittest.TestCase):
    def _task_instance(self, folder):
        ti = Mock(dag_id="dag", run_id="run", task_id="task", try_number=1)
        log_dir = os.path.join(folder, "dag_id=dag", "run_id=run", "task_id=task")
        os.makedirs(log_dir)
        with open(os.path.join(log_dir, "attempt=1.log"), "w") as fd:
            fd.write("the airflow log")
        return ti

    def _put_payloads(self, client):
        return [
            call.kwargs["payload"] for call in client.raw.put_api_for_id.call_args_list
        ]

    def test_try_to_save_airflow_log_without_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ti = self._task_instance(folder)
            client = Mock()
            du.try_to_save_airflow_log(client, "exec-id", ti, folder)
        self.assertEqual([dict(log_text="the airflow log")], self._put_payloads(client))

    def test_try_to_save_airflow_log_with_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ti = self._task_instance(folder)
            client = Mock()
            du.try_to_save_airflow_log(client, "exec-id", ti, folder, state=-1)
        self.assertEqual(
            [dict(log_text="the airflow log", state=-1)], self._put_payloads(client)
        )

    @patch("cornflow_client.airflow.dag_utilities.connect_to_cornflow")
    def test_cf_solve_error_log_keeps_error_state(self, connect):
        client = Mock()
        client.get_data.return_value = dict(
            data={}, solution_data=None, config={"msg": False}, id="inst-id"
        )
        connect.return_value = client

        def failing_solver(*args):
            raise ValueError("boom")

        with tempfile.TemporaryDirectory() as folder:
            ti = self._task_instance(folder)
            with self.assertRaises(du.AirflowDagException):
                self._run_cf_solve(failing_solver, ti, folder)

        payloads = self._put_payloads(client)
        self.assertIn(dict(state=-1), payloads)
        log_payloads = [p for p in payloads if "log_text" in p]
        self.assertEqual(1, len(log_payloads))
        self.assertEqual(-1, log_payloads[0]["state"])
        # the last write to the execution must not be a state-less one
        self.assertIn("state", payloads[-1])

    def _run_cf_solve(self, fun, ti, folder):
        with patch(
            "cornflow_client.airflow.dag_utilities.get_base_log_folder",
            return_value=folder,
        ):
            return du.cf_solve(
                fun,
                "dag",
                {},
                ti=ti,
                dag_run=Mock(conf={"exec_id": "exec-id"}),
            )
