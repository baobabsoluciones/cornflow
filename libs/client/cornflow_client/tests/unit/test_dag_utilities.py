import unittest
import os
import tempfile

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


class TestDagUtilities(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for log files
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base_log = self.tmpdir.name
        # Sample TaskInstance-like object
        class TI:
            pass
        self.ti = TI()
        self.ti.dag_id = "test_dag"
        self.ti.task_id = "test_task"
        self.ti.run_id = "manual__2025-06-12T00:00:00"
        self.ti.try_number = 1

        # Construct expected log path
        self.log_path = du.construct_log_path(self.ti, self.base_log)
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_detect_memory_error_from_logs_not_exists(self):
        # Non-existent path should return False
        self.assertFalse(du.detect_memory_error_from_logs("/no/such/path.log"))

    def test_detect_memory_error_from_logs_false(self):
        # Create a log without error patterns
        with open(self.log_path, 'w') as f:
            f.write("All good, finished without issues\n")
        self.assertFalse(du.detect_memory_error_from_logs(self.log_path))

    def test_detect_memory_error_from_logs_true(self):
        # Create a log with an OOM pattern
        with open(self.log_path, 'w') as f:
            f.write("Some output... MemoryError occurred at line 42\n")
        self.assertTrue(du.detect_memory_error_from_logs(self.log_path))

    def test_construct_log_path_format(self):
        expected = os.path.join(
            self.base_log,
            "test_dag",
            "test_task",
            "2025-06-12T00:00:00",
            "1.log"
        )
        self.assertEqual(expected, du.construct_log_path(self.ti, self.base_log))

    @patch('airflow.configuration.conf.get')
    @patch('cornflow_client.airflow.dag_utilities.connect_to_cornflow')
    @patch('airflow.secrets.environment_variables.EnvironmentVariablesBackend')
    @patch('cornflow_client.airflow.dag_utilities.detect_memory_error_from_logs')
    def test_callback_on_task_failure_oom(self, mock_detect, mock_env, mock_connect):
        # Simulate OOM detection
        mock_detect.return_value = True
        # Prepare client mock
        client = Mock()
        mock_connect.return_value = client

        # Write a dummy log
        with open(self.log_path, 'w') as f:
            f.write("OOMKilled caused the crash\n")

        # Prepare context
        ti = self.ti
        # monkey-patch log_filepath property
        ti.log_filepath = self.log_path
        dag_run = Mock(conf={'exec_id': 'exec123'})
        context = {'ti': ti, 'dag_run': dag_run}

        # Run callback
        du.callback_on_task_failure(context)

        # Assert update_status called with -8
        client.update_status.assert_called_once_with('exec123', {'status': -8})
        # Assert log snippet sent
        client.raw.put_api_for_id.assert_called_once()
        args, kwargs = client.raw.put_api_for_id.call_args
        self.assertEqual(kwargs['id'], 'exec123')
        self.assertIn('log_text', kwargs['payload'])

    @patch('airflow.configuration.conf.get')
    @patch('cornflow_client.airflow.dag_utilities.connect_to_cornflow')
    @patch('airflow.secrets.environment_variables.EnvironmentVariablesBackend')
    @patch('cornflow_client.airflow.dag_utilities.detect_memory_error_from_logs')
    def test_callback_on_task_failure_generic(self, mock_detect, mock_env, mock_connect):
        # Simulate no OOM detection
        mock_detect.return_value = False
        # Prepare client mock
        client = Mock()
        mock_connect.return_value = client

        # Write a dummy log
        with open(self.log_path, 'w') as f:
            f.write("Unexpected exception occurred\n")

        # Prepare context
        ti = self.ti
        ti.log_filepath = self.log_path
        dag_run = Mock(conf={'exec_id': 'exec456'})
        context = {'ti': ti, 'dag_run': dag_run}

        # Run callback
        du.callback_on_task_failure(context)

        # Assert update_status called with -1
        client.update_status.assert_called_once_with('exec456', {'status': -1})
        client.raw.put_api_for_id.assert_called_once()

    def test_callback_on_task_failure_early_return(self):
        # Missing ti or dag_run => no exception
        context = {}
        # Should not raise
        du.callback_on_task_failure(context)

if __name__ == '__main__':
    unittest.main()
