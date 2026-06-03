import cornflow_client.airflow.dag_utilities as utils
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend

from update_all_schemas import get_new_apps


def create_dag(app):
    """
    Create DAG for model resolution
    """

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
        **kwargs,
    )
    with dag:
        notify = getattr(app, "notify", True)
        if not notify:
            PythonOperator(task_id=app.name, python_callable=solve)
        else:
            PythonOperator(
                task_id=app.name,
                python_callable=solve,
                on_failure_callback=utils.callback_email,
            )

    return dag


def create_check_kpis_dag(app):
    """
    Create DAG for checking data and generating KPIs
    """

    def check_generate_kpis(**kwargs):
        return utils.cf_check_generate_kpis_app(
            app, EnvironmentVariablesBackend(), **kwargs
        )

    if app.default_args_checks_kpis is not None:
        default_args_checks_kpis = app.default_args_checks_kpis
    else:
        default_args_checks_kpis = utils.default_args

    kwargs_checks_kpis = {}
    if app.extra_args_checks_kpis is not None:
        kwargs_checks_kpis = app.extra_args_checks_kpis

    dag_name = utils.get_workflow_name_check_kpis(app.name)
    dag = DAG(
        dag_name,
        description=f"Checks and KPIs generation for {app.name}",
        default_args=default_args_checks_kpis,
        schedule_interval=None,
        tags=["check_kpis"],
        **kwargs_checks_kpis,
    )
    with dag:
        notify = getattr(app, "notify", True)
        if not notify:
            PythonOperator(task_id=dag_name, python_callable=check_generate_kpis)
        else:
            PythonOperator(
                task_id=dag_name,
                python_callable=check_generate_kpis,
                on_failure_callback=utils.callback_email,
            )

    return dag


for app in get_new_apps():
    globals()[app.name] = create_dag(app)
    dag_name_check_kpis = utils.get_workflow_name_check_kpis(app.name)
    globals()[dag_name_check_kpis] = create_check_kpis_dag(app)
