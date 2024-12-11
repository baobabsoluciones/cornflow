"""
Test utility tools and helper functions.

This module provides utility functions and tools to assist with testing,
including mocking, data manipulation, and test setup helpers.

Functions
---------
patch_af_client
    Patches an Airflow client mock with standard test configurations
"""

from unittest.mock import Mock


def patch_af_client(Airflow_mock):
    """
    Patches an Airflow client mock with standard test configurations.

    This function configures a mock Airflow client with common test settings,
    including DAG status checks, execution states, and connection parameters.

    :param Airflow_mock: The mock object to be configured for Airflow client testing
    :type Airflow_mock: unittest.mock.Mock

    :return: The configured mock Airflow client
    :rtype: unittest.mock.Mock

    :Example:

    .. code-block:: python

        with patch('cornflow.endpoints.airflow.Airflow') as af_mock:
            patch_af_client(af_mock)
            # Test code using mocked Airflow client
    """
    af_client = Airflow_mock.return_value
    af_client.is_alive.return_value = True
    af_client.get_dag_status.return_value = {
        "status": "success",
        "execution_date": "2020-01-01T00:00:00+00:00",
    }
    af_client.get_one_execution.return_value = {
        "state": "success",
        "start_date": "2020-01-01T00:00:00+00:00",
        "end_date": "2020-01-01T00:01:00+00:00",
    }
    af_client.get_dag_info.return_value = {}
    af_client.get_one_variable.return_value = {}
    af_client.get_all_schemas.return_value = []
    return af_client
