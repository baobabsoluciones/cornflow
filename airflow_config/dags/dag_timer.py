from airflow import DAG, AirflowException
from airflow.operators.python_operator import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
import time
from datetime import datetime, timedelta


# Following are defaults which can be overridden later on
default_args = {
    'owner': 'baobab',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}

dag = DAG('timer', default_args=default_args, schedule_interval=None)

def run(**kwargs):
    seconds = kwargs["dag_run"].conf.get('seconds', 60)
    print("sleep started for {} seconds".format(seconds))
    time.sleep(seconds)
    print("sleep finished")
    return "True"


solve_task = PythonOperator(
    task_id='timer',
    provide_context=True,
    python_callable=run,
    dag=dag,
)
