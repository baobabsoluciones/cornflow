from airflow import DAG
from airflow.operators.python import PythonOperator
import time
from datetime import datetime, timedelta
from cornflow_client import get_empty_schema


# Following are defaults which can be overridden later on
name = "timer"
default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retry_delay": timedelta(minutes=1),
    "schedule_interval": None,
}
dag = DAG(name, default_args=default_args, schedule_interval=None)


def solve(**kwargs):
    config = kwargs["dag_run"].conf
    seconds = config.get("seconds", 60)
    seconds = config.get("timeLimit", seconds)

    print("sleep started for {} seconds".format(seconds))
    time.sleep(seconds)
    print("sleep finished")
    return "True"


config = solution = get_empty_schema()
instance = get_empty_schema()


solve_task = PythonOperator(
    task_id=name,
    provide_context=True,
    python_callable=solve,
    dag=dag,
)
