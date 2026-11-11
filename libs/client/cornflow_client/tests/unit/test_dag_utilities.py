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

    def _failed_task(self, layout):
        """A temp log folder with one task log written in ``layout``; returns (folder, ti)."""
        import os
        import tempfile

        base = tempfile.mkdtemp()
        ti = Mock(dag_id="rostering", task_id="rostering", run_id="manual__2026-11-11T20:21:33+00:00", try_number=1)
        ti.execution_date = None
        path = os.path.join(base, *layout)
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as fd:
            fd.write("task started\n")
        return base, ti

    def test_airflow_log_of_a_failed_execution_is_saved_with_the_traceback(self):
        # Airflow 2 layout, found through the configured template
        base, ti = self._failed_task(
            ["dag_id=rostering", "run_id=manual__2026-11-11T20:21:33+00:00", "task_id=rostering", "attempt=1.log"]
        )
        template = "dag_id={{ ti.dag_id }}/run_id={{ ti.run_id }}/task_id={{ ti.task_id }}/attempt={{ try_number }}.log"
        client = Mock()

        du.try_to_save_airflow_log(client, "exec1", ti, base, "KeyError: (36, 3)", template)

        payload = client.raw.put_api_for_id.call_args.kwargs["payload"]
        self.assertIn("task started", payload["log_text"])
        self.assertIn("KeyError: (36, 3)", payload["log_text"])
        # the endpoint turns a missing state into "correct": the failure state must travel with the log
        self.assertEqual(payload["state"], -1)

    def test_the_log_layout_of_old_airflow_versions_is_still_found(self):
        base, ti = self._failed_task(["rostering", "rostering", "2026-11-11T20:21:33+00:00", "1.log"])
        client = Mock()

        du.try_to_save_airflow_log(client, "exec1", ti, base, "boom")

        self.assertIn("task started", client.raw.put_api_for_id.call_args.kwargs["payload"]["log_text"])

    def test_without_a_log_file_the_traceback_is_still_saved(self):
        import tempfile

        ti = Mock(dag_id="d", task_id="t", run_id="r", try_number=1)
        ti.execution_date = None
        client = Mock()

        du.try_to_save_airflow_log(client, "exec1", ti, tempfile.mkdtemp(), "boom")

        self.assertEqual(client.raw.put_api_for_id.call_args.kwargs["payload"]["log_text"].strip(), "boom")
