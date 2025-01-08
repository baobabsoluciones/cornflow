import importlib as il
import os
import sys
from datetime import datetime, timedelta
from typing import List
from warnings import warn

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.utils.db import create_session
from cornflow_client import ApplicationCore
from cornflow_client.airflow.dag_utilities import callback_email

default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "catchup": False,
}

schemas = ["instance", "solution", "config"]


def get_new_apps() -> List[ApplicationCore]:
    # we need to run this to be sure to import modules
    import_dags()
    new_apps = ApplicationCore.__subclasses__()
    return [app_class() for app_class in new_apps]


def import_dags():
    sys.path.append(os.path.dirname(__file__))
    _dir = os.path.dirname(__file__)
    print(f"looking for apps in dir={_dir}")
    files = os.listdir(_dir)
    print(f"Files are: {files}")
    # we go file by file and try to import it if matches the filters
    # TODO: here we should implement a .dagignore file to avoid files that could be on the folder
    for dag_module in files:
        filename, ext = os.path.splitext(dag_module)

        if ext not in [".py", ""]:
            continue

        if filename.startswith(
            (
                ".",
                "__",
                "scripts",
                "documentation",
                "tests",
                "activate_dags",
            )
        ):
            continue

        try:
            _import_file(filename)
            print(f"Imported {filename}")
        except Exception as e:
            raise e


def _import_file(filename):
    return il.import_module(filename)


def get_schemas_dag_file(_module):
    contents = {k: getattr(_module, k) for k in schemas}
    return contents


def get_all_schemas(apps):
    apps_names = [app.name for app in apps]
    if len(apps):
        print(f"Found the following apps: {apps_names}")
    else:
        print("No apps were found to update")
    schemas_new = {app.name: app.get_schemas() for app in apps}
    print(f"Found the following new apps: {apps_names}")
    return schemas_new


def get_all_example_data(apps):
    apps_names = [app.name for app in apps]
    if len(apps):
        print(f"Found the following apps: {apps_names}")
    else:
        print("No apps were found to update")
    example_data_new = {}

    for app in apps:
        tests = app.test_cases
        print(f"App: {app.name} has {len(tests)} examples")

        for pos, test in enumerate(tests):
            if isinstance(test, dict):
                continue

            elif isinstance(test, tuple):
                warn(
                    "The tests as a tuple is no loger supported, please upgrade to the new test cases structure"
                )
                temp_example = {
                    "name": "No available name for the test",
                    "instance": test[0],
                    "solution": test[1],
                }
                tests[pos] = temp_example

        if len(tests) > 0:
            example_data_new[f"z_{app.name}_examples"] = tests

    print(f"Found the following new apps: {apps_names}")
    return example_data_new


def update_all_schemas(**kwargs):
    sys.setrecursionlimit(2000)

    # first we delete all variables (this helps to keep it clean)
    with create_session() as session:
        current_vars = set(var.key for var in session.query(Variable))
        for _var in current_vars:
            Variable.delete(_var, session)

    # we update all schemas that we found:
    apps = get_new_apps()

    schemas = get_all_schemas(apps)

    for key, value in schemas.items():
        Variable.set(key=key, value=value, serialize_json=True)

    # we update all examples that we found:
    example_data = get_all_example_data(apps)
    for key, value in example_data.items():
        Variable.set(key=key, value=value, serialize_json=True)


dag = DAG(
    "update_all_schemas",
    default_args=default_args,
    catchup=False,
    tags=["internal"],
    schedule_interval="@hourly",
)

update_schema2 = PythonOperator(
    task_id="update_all_schemas",
    provide_context=True,
    python_callable=update_all_schemas,
    dag=dag,
    on_failure_callback=callback_email,
)


if __name__ == "__main__":
    update_all_schemas()
