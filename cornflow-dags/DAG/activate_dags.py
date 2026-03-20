import os

import cornflow_client.airflow.dag_utilities as utils
from airflow import DAG
from airflow.operators.python import PythonOperator, ExternalPythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend

from update_all_schemas import get_new_apps

VENVS_BASE_DIR = os.getenv("CORNFLOW_VENVS_DIR", "/usr/local/airflow/venvs")


def create_dag(app):
    def solve(**kwargs):
        import cornflow_client.airflow.dag_utilities as utils
        from airflow.secrets.environment_variables import EnvironmentVariablesBackend

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
        venv_name = getattr(app, "venv", None)

        operator_kwargs = {
            "task_id": app.name,
            "python_callable": solve,
        }

        if notify:
            operator_kwargs["on_failure_callback"] = utils.callback_email

        if venv_name:
            venv_python = os.path.join(VENVS_BASE_DIR, venv_name, "bin", "python")
            ExternalPythonOperator(python=venv_python, **operator_kwargs)
        else:
            PythonOperator(**operator_kwargs)

    return dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
