# Full imports
import json
import os

# Partial imports
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from cornflow_client.airflow.dag_utilities import connect_to_cornflow
from datetime import datetime, timedelta


default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2022, 5, 23),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "catchup": False,
}


def call_cornflow(**kwargs):

    cf_client = connect_to_cornflow(EnvironmentVariablesBackend())

    cwd = os.path.dirname(os.path.realpath(__file__))
    PULP_EXAMPLE = os.path.join(cwd, './pulp_example_data.json')
    with open(PULP_EXAMPLE) as fd:
        data = json.load(fd)
    instance = cf_client.create_instance(
        data=data,
        name="Airflow auto",
        description="",
        schema="solve_model_dag",
    )
    config = {"solver": "PULP_CBC_CMD", "timeLimit": 60}

    cf_client.create_execution(
        instance_id=instance['id'],
        config=config,
        name="Airflow auto",
        description="",
        schema="solve_model_dag",
    )


dag = DAG(
    "call_cornflow", default_args=default_args, catchup=False, tags=["internal"], schedule_interval=timedelta(hours=2),
)

call_cornflow_2 = PythonOperator(
    task_id="call_cornflow",
    provide_context=True,
    python_callable=call_cornflow,
    dag=dag,
)

if __name__ == "__main__":
    call_cornflow()
