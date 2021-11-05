from airflow import DAG
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
import cornflow_client.airflow.dag_utilities as utils
from update_all_schemas import get_new_apps
from airflow.operators.python import PythonOperator


def create_dag(app):
    def solve(**kwargs):
        return utils.cf_solve_app(app, EnvironmentVariablesBackend(), **kwargs)

    dag = DAG(app.name, default_args=utils.default_args, schedule_interval=None)
    with dag:
        t1 = PythonOperator(task_id=app.name, python_callable=solve)
    return dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
