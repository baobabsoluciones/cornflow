import logging
import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from airflow.utils.db import create_session
from cornflow_client import CornFlowApiError
from cornflow_client.airflow.dag_utilities import connect_to_cornflow

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


def run_examples(**kwargs):
    with create_session() as session:
        current_examples = {
            var.key: var.get_val()
            for var in session.query(Variable)
            if "_examples" in var.key
        }

    logger.info(current_examples)

    cf_client = connect_to_cornflow(EnvironmentVariablesBackend())
    executions = []

    for key, instance in current_examples.items():
        schema = key.split("z_")[1].split("_examples")[0]

        try:
            response = cf_client.create_instance(
                data=instance, name=f"Automatic_instance_run_{schema}", schema=schema
            )
        except CornFlowApiError as e:
            logger.info(e)
            logger.info(
                f"Instance example for schema {schema} had an error on creation"
            )
            continue

        instance_id = response["id"]

        config = {"solver": "PULP_CBC_CMD", "time_limit": 60, "msg": True}

        try:
            response = cf_client.create_execution(
                instance_id=instance_id,
                config=config,
                name=f"Automatic_execution_run_{schema}",
                schema=schema,
            )
        except CornFlowApiError as e:
            logger.info(e)
            logger.info(
                f"Execution example for schema {schema} had an error on creation"
            )
            continue

        execution_id = response["id"]
        executions.append((execution_id, schema))

    limit = (len(executions) + 1) * 60
    start = datetime.utcnow()

    while executions and datetime.utcnow() - start < timedelta(seconds=limit):
        for index, (execution, schema) in enumerate(executions):
            try:
                response = cf_client.get_status(execution_id=execution)
            except CornFlowApiError as e:
                logger.info(e)
                logger.info(
                    f"Execution {execution} of schema {schema} had an error on status retrieval"
                )
                executions.pop(index)
                continue

            if response["status"] in (1, 2):
                logger.info(
                    f"Execution {execution} if schema {schema} finished successfully"
                )
                executions.pop(index)
            elif response["status"] in (-1, -2, -3, -4, -5, -6):
                logger.info(f"Execution {execution} of schema {schema} failed")
                executions.pop(index)
            else:
                continue

        time.sleep(15)

    if len(executions):
        for execution, schema in executions:
            logger.info(
                f"Execution {execution} of schema {schema} could not be checked"
            )

    logger.info("Automatic test process finished")


dag = DAG(
    "run_deployed_models",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
)

run_examples_task = PythonOperator(
    task_id="run_examples",
    python_callable=run_examples,
    provide_context=True,
    dag=dag,
)
