from unittest.mock import Mock


def patch_af_client(af_client_class):
    af_client_mock = Mock()
    responses_mock = Mock()
    responses_mock.json.return_value = {"is_paused": False, "dag_run_id": "12345", "state": "success"}
    af_client_mock.is_alive.return_value = True
    af_client_mock.get_dag_info.return_value = responses_mock
    af_client_mock.run_dag.return_value = responses_mock
    af_client_mock.get_dag_run_status.return_value = responses_mock
    af_client_mock.set_dag_run_to_fail.return_value = None
    af_client_class.from_config.return_value = af_client_mock