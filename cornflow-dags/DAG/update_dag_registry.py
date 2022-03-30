# Full imports


# Partial imports
from airflow import DAG
from airflow.models import DagModel
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from airflow.utils.db import create_session
from cornflow_client import CornFlow
from cornflow_client.airflow.dag_utilities import connect_to_cornflow
from datetime import datetime, timedelta

default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "schedule_interval": "@hourly",
    "catchup": False,
}


def update_dag_registry(**kwargs):
    with create_session() as session:

        model_dags = [
            dag
            for dag in session.query(DagModel)
            for tag in dag.tags
            if tag.name == "model"
        ]
        print(f"MODEL DAGS: {model_dags}")
        cf_client = connect_to_cornflow(EnvironmentVariablesBackend())
        deployed_dags = [
            dag["id"] for dag in cf_client.get_deployed_dags(encoding="br")
        ]
        print(f"DEPLOYED DAGS: {deployed_dags}")
        for model in model_dags:
            if model.dag_id not in deployed_dags:
                response = cf_client.create_deployed_dag(
                    name=model.dag_id, description=model.description, encoding="br"
                )
                print(f"DAG: {response['id']} registered")


dag = DAG(
    "update_dag_registry", default_args=default_args, catchup=False, tags=["internal"]
)

update_dag_registry_2 = PythonOperator(
    task_id="update_dag_registry",
    provide_context=True,
    python_callable=update_dag_registry,
    dag=dag,
)

if __name__ == "__main__":
    update_dag_registry()
