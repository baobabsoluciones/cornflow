from airflow import DAG
from airflow.operators.python import PythonOperator
import time
try:
    import utils
except ImportError:
    import DAG.utils as utils

# Following are defaults which can be overridden later on
name = 'timer'
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)


def solve(**kwargs):
    config = kwargs["dag_run"].conf
    seconds = config.get('seconds', 60)
    seconds = config.get('timeLimit', seconds)

    print("sleep started for {} seconds".format(seconds))
    time.sleep(seconds)
    print("sleep finished")
    return "True"


instance = dict(type="object", properties=dict(seconds=dict(type="integer")), required=[])
instance['$schema'] = "http://json-schema.org/draft-07/schema#"
solution = instance

solve_task = PythonOperator(
    task_id=name,
    provide_context=True,
    python_callable=solve,
    dag=dag,
)
