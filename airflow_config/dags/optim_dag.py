from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
import model_functions as mf

dag = DAG(mf.name, default_args=mf.utils.default_args, schedule_interval=None)


def run_solve(**kwargs):
    return mf.utils.cf_solve(mf.solve, mf.name, EnvironmentVariablesBackend(), **kwargs)


solve_task = PythonOperator(
    task_id=mf.name,
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)
