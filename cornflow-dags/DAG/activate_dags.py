import cornflow_client.airflow.dag_utilities as utils
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from airflow.decorators import dag, task
from airflow.models.baseoperator import chain
from airflow.exceptions import AirflowSkipException

from update_all_schemas import get_new_apps


def create_dag(app):

    if app.default_args is not None:
        default_args = app.default_args
    else:
        default_args = utils.default_args

    kwargs = {}
    if app.extra_args is not None:
        kwargs = app.extra_args

    @dag(
        app.name,
        description=app.description,
        default_args=default_args,
        schedule_interval=None,
        tags=["model"],
        **kwargs
    )
    def taskflow_dag():
        @task
        def solve_app():
            def solve(**kwargs):
                return utils.cf_solve_app(app, EnvironmentVariablesBackend(), **kwargs)

            notify = getattr(app, "notify", True)
            if not notify:
                return PythonOperator(task_id=app.name, python_callable=solve)
            else:
                return PythonOperator(
                    task_id=app.name,
                    python_callable=solve,
                    on_failure_callback=utils.callback_email,
                )

        @task
        def run_report():
            def run(**kwargs):
                return utils.cf_report(app, EnvironmentVariablesBackend(), **kwargs)

            file_name = PythonOperator(
                task_id=app.name + "_report", python_callable=run
            )
            return dict(file_name=file_name)

        # Define dependencies and call task functions
        chain(solve_app(), run_report())

    return taskflow_dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
