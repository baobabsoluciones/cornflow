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
            PythonOperator(task_id=app.name,
                           python_callable=solve,
                           provide_context=True,
                           on_failure_callback=utils.callback_on_task_failure,
            )
        else:

            # Define a failure callback that handles both task failure and email notification
            def failure_and_email(context):
                utils.callback_on_task_failure(context)
                utils.callback_email(context)

            PythonOperator(
                task_id=app.name,
                python_callable=solve,
                on_failure_callback=failure_and_email,
            )

    return dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
