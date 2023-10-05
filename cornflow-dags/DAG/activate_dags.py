import cornflow_client.airflow.dag_utilities as utils
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend

from update_all_schemas import get_new_apps


def create_dag(app):
    def solve(**kwargs):
        return utils.cf_solve_app(app, EnvironmentVariablesBackend(), **kwargs)

    if app.default_args is not None:
        default_args = app.default_args
    else:
        default_args = utils.default_args

    kwargs = {}
    if app.extra_args is not None:
        kwargs = app.extra_args

    dag = DAG(
        app.name,
        description=app.description,
        default_args=default_args,
        schedule_interval=None,
        tags=["model"],
        **kwargs
    )
    with dag:
        notify = getattr(app, "notify", True)
        if not notify:
            t1 = PythonOperator(task_id=app.name, python_callable=solve)
        else:
            t1 = PythonOperator(
                task_id=app.name,
                python_callable=solve,
                on_failure_callback=utils.callback_email,
            )

    return dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
