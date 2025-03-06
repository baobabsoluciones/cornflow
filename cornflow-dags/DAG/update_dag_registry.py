from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.models import DagModel
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from airflow.utils.db import create_session
from cornflow_client.airflow.dag_utilities import connect_to_cornflow

from update_all_schemas import get_new_apps

default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "catchup": False,
}

logger = logging.getLogger("airflow.task")


def update_dag_registry(**kwargs):
    with create_session() as session:
        model_dags = [
            dag
            for dag in session.query(DagModel)
            for tag in dag.tags
            if tag.name == "model"
        ]
        logger.info(f"MODEL DAGS: {model_dags}")
        cf_client = connect_to_cornflow(EnvironmentVariablesBackend())
        deployed_dags = [
            dag["id"] for dag in cf_client.get_deployed_dags(encoding="br")
        ]
        logger.info(f"DEPLOYED DAGS: {deployed_dags}")
        all_apps = dict()
        for app in get_new_apps():
            all_apps[app.name] = app
        for model in model_dags:
            if model.dag_id not in all_apps:
                logger.warning(f"App {model.dag_id} is registered in Airflow database but there is no app for it. Skipping")
                continue
            app = all_apps[model.dag_id]
            if model.dag_id not in deployed_dags:
                response = cf_client.create_deployed_dag(
                    name=model.dag_id,
                    description=model.description,
                    instance_schema=app.instance.schema,
                    instance_checks_schema=app.instance.schema_checks,
                    solution_schema=app.solution.schema,
                    solution_checks_schema=app.solvers[
                        app.get_default_solver_name()
                    ].schema_checks,
                    config_schema=app.schema,
                    encoding="br",
                )
                logger.info(f"DAG: {response['id']} registered")
            else:
                # Even if the dag is registered, we still update its schemas
                response = cf_client.put_deployed_dag(
                    dag_id=model.dag_id,
                    data=dict(
                        description=model.description,
                        instance_schema=app.instance.schema,
                        instance_checks_schema=app.instance.schema_checks,
                        solution_schema=app.solution.schema,
                        solution_checks_schema=app.get_solver(
                            app.get_default_solver_name()
                        ).schema_checks,
                        config_schema=app.schema,
                    ),
                    encoding="br",
                )
                logger.info(f"DAG: {model.dag_id} registered")


dag = DAG(
    "update_dag_registry",
    default_args=default_args,
    catchup=False,
    tags=["internal"],
    schedule_interval="@hourly",
)

update_dag_registry_2 = PythonOperator(
    task_id="update_dag_registry",
    provide_context=True,
    python_callable=update_dag_registry,
    dag=dag,
)

if __name__ == "__main__":
    update_dag_registry()