# Imports from external libraries
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from cornflow_client import CornFlowApiError
from cornflow_client.airflow.dag_utilities import connect_to_cornflow
from datetime import datetime, timedelta
from time import sleep
from urllib.parse import urljoin
import requests


default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "catchup": False,
}


def connection_cleanup():
    """
    Dag to clean up expired connections from the backend
    """
    client = None

    secrets = EnvironmentVariablesBackend()
    max_attempts = 3
    retry_sleep_seconds = 5
    attempts = 0
    while attempts < max_attempts:
        try:
            client = connect_to_cornflow(secrets)
            break
        except CornFlowApiError as err:
            attempts += 1
            sleep(retry_sleep_seconds)

    if client is None:
        raise CornFlowApiError(
            f"Could not log in to Cornflow. {attempts}/{max_attempts} failed login attempts"
        )

    response = requests.delete(
        urljoin(client.url, f"/connection-cleanup/"),
        headers={
            "Authorization": "access_token " + client.token,
            "Content-Encoding": "br",
        },
    )
    if response.status_code != 200:
        raise CornFlowApiError(f"Could not clean up the database: {response.json()}")
    print("Cleanup finished. ", response.json()["message"])


dag = DAG(
    "connection_cleanup",
    default_args=default_args,
    catchup=False,
    tags=["internal"],
    schedule_interval="@daily",
    start_date=datetime(2024, 6, 1, 0, 0, 0),
)

connection_cleanup_operator = PythonOperator(
    task_id="connection_cleanup",
    provide_context=True,
    python_callable=connection_cleanup,
    dag=dag,
)

if __name__ == "__main__":
    connection_cleanup()
