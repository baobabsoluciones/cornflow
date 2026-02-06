"""
Creates one DAG per application for running instance checks and/or solution checks + KPIs.
These DAGs do not use the solver and can run many executions in parallel.

- Instance checks only: execution has no solution_data -> run instance checks, save to instance.checks.
- Solution checks + KPIs: execution has solution_data -> run solution checks, save to execution.checks;
  if no errors, run generate_kpis and save to execution.kpis.
"""

import cornflow_client.airflow.dag_utilities as utils
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend

from update_all_schemas import get_new_apps

CHECK_DAG_SUFFIX = "_checks"


def create_checks_dag(app):
    def run_checks_and_kpis(**kwargs):
        return utils.cf_checks_and_kpis(app, EnvironmentVariablesBackend(), **kwargs)

    if app.default_args is not None:
        default_args = app.default_args
    else:
        default_args = utils.default_args

    kwargs = {}
    if app.extra_args is not None:
        kwargs = app.extra_args

    dag = DAG(
        app.name + CHECK_DAG_SUFFIX,
        description=(app.description or "") + " (checks and KPIs only)",
        default_args=default_args,
        schedule_interval=None,
        tags=["model", "checks"],
        **kwargs,
    )
    with dag:
        notify = getattr(app, "notify", True)
        if not notify:
            PythonOperator(
                task_id=app.name + CHECK_DAG_SUFFIX,
                python_callable=run_checks_and_kpis,
            )
        else:
            PythonOperator(
                task_id=app.name + CHECK_DAG_SUFFIX,
                python_callable=run_checks_and_kpis,
                on_failure_callback=utils.callback_email,
            )

    return dag


for app in get_new_apps():
    globals()[app.name + CHECK_DAG_SUFFIX] = create_checks_dag(app)
