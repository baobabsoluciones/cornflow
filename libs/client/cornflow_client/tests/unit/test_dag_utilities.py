import unittest
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
        for (conn_str, user_info, url) in conn_uris:
            secrets.get_conn_uri.return_value = conn_str
            du.connect_to_cornflow(secrets)
            client_instance.login.assert_called_with(
                username=user_info[0], pwd=user_info[1]
            )
            CornFlow.assert_called_with(url=url)
