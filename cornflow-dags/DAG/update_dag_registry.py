from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
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
    # Airflow 3 no permite acceso directo a la BBDD por ORM desde una tarea (RuntimeError:
    # "Direct database access via the ORM is not allowed in Airflow 3.0"), así que ya no se puede
    # hacer `session.query(DagModel)` para encontrar los DAGs con tag "model". No hace falta:
    # `get_new_apps()` ya devuelve exactamente esas mismas apps (activate_dags.py crea un DAG por
    # cada una, con `tags=["model"]` y `dag_id == app.name`), así que es la misma información sin
    # pasar por la BBDD. `app.description` sustituye a `model.description` (mismo valor: es lo que
    # activate_dags.py usa para crear el DAG).
    cf_client = connect_to_cornflow(EnvironmentVariablesBackend())
    deployed_dags = [dag["id"] for dag in cf_client.get_deployed_dags(encoding="br")]
    logger.info(f"DEPLOYED DAGS: {deployed_dags}")

    apps = get_new_apps()
    logger.info(f"MODEL APPS: {[app.name for app in apps]}")

    for app in apps:
        solver = app.get_solver(app.get_default_solver_name())
        if app.name not in deployed_dags:
            response = cf_client.create_deployed_dag(
                name=app.name,
                description=app.description,
                instance_schema=app.instance.schema,
                instance_checks_schema=app.instance.schema_checks,
                solution_schema=app.solution.schema,
                solution_checks_schema=solver.schema_checks,
                kpis_schema=solver.schema_kpis,
                config_schema=app.schema,
                encoding="br",
            )
            logger.info(f"DAG: {response['id']} registered")
        else:
            # Even if the dag is registered, we still update its schemas
            response = cf_client.put_deployed_dag(
                dag_id=app.name,
                data=dict(
                    description=app.description,
                    instance_schema=app.instance.schema,
                    instance_checks_schema=app.instance.schema_checks,
                    solution_schema=app.solution.schema,
                    solution_checks_schema=solver.schema_checks,
                    kpis_schema=solver.schema_kpis,
                    config_schema=app.schema,
                ),
                encoding="br",
            )
            logger.info(f"DAG: {app.name} registered")


dag = DAG(
    "update_dag_registry",
    default_args=default_args,
    catchup=False,
    tags=["internal"],
    schedule="@hourly",
)

update_dag_registry_2 = PythonOperator(
    task_id="update_dag_registry",
    python_callable=update_dag_registry,
    dag=dag,
)

if __name__ == "__main__":
    update_dag_registry()
