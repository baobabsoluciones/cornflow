import logging
import time
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sdk import Variable
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from cornflow_client import CornFlowApiError
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


def run_examples(**kwargs):
    # Airflow 3 does not allow direct database access from a task, so the example
    # variables cannot be listed through the ORM anymore. update_all_schemas stores one
    # variable per app under the key f"z_{app.name}_examples", so we read those directly.
    current_examples = {}
    for app in get_new_apps():
        key = f"z_{app.name}_examples"
        examples = Variable.get(key, default=None, deserialize_json=True)
        if examples:
            current_examples[key] = examples

    cf_client = connect_to_cornflow(EnvironmentVariablesBackend())
    executions = []

    for key, example_list in current_examples.items():
        schema = key.split("z_")[1].split("_examples")[0]
        # TODO: maybe we want to run all available test instances?
        instance = example_list[0]["instance"]
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

        config = {"timeLimit": 60, "msg": True}

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
    start = datetime.now(timezone.utc)

    while executions and datetime.now(timezone.utc) - start < timedelta(seconds=limit):
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

            if response["state"] in (1, 2):
                logger.info(
                    f"Execution {execution} of schema {schema} finished successfully"
                )
                executions.pop(index)
            elif response["state"] in (-1, -2, -3, -4, -5, -6):
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
    schedule=None,
    catchup=False,
)

run_examples_task = PythonOperator(
    task_id="run_examples",
    python_callable=run_examples,
    dag=dag,
)
