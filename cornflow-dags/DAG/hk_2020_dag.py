from airflow import DAG, AirflowException
from airflow.operators.python_operator import PythonOperator, PythonVirtualenvOperator
from cornflow_client import CornFlow
from datetime import datetime, timedelta
from utils import get_arg, get_requirements
from hk_2020_functions import solve_hk, test_hk


# Following are defaults which can be overridden later on
# TODO: clean this
default_args = {
    'owner': 'hugo',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}

dag2 = DAG('hk_2020_dag', default_args=default_args, schedule_interval=None)

hackaton_task = PythonOperator(
    task_id='hk_2020_task',
    python_callable=solve_hk,
    dag=dag2
)

# hackaton_task = PythonOperator(
#     task_id='hk_2020_task',
#     python_callable=test_hk,
#     dag=dag2
# )



    
    
    
    
    
    
    
    