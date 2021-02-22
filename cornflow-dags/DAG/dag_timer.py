from airflow import DAG
from airflow.operators.python import PythonOperator
import time
from utils import default_args

# Following are defaults which can be overridden later on

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
