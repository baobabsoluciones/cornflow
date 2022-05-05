# General imports
import importlib as il
import os
import sys

# Partial imports
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow import DAG
from airflow.utils.db import create_session
from datetime import datetime, timedelta
from typing import List

# Import from cornflow environment
from cornflow_client import ApplicationCore


default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "schedule_interval": "@hourly",
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
    print("looking for apps in dir={}".format(_dir))
    files = os.listdir(_dir)
    print("Files are: {}".format(files))
    # we go file by file and try to import it if matches the filters
    for dag_module in files:
        filename, ext = os.path.splitext(dag_module)
        if ext not in [".py", ""]:
            continue
        if filename in ["activate_apps"]:
            continue
        try:
            _import_file(filename)
        except Exception as e:
            continue


def _import_file(filename):
    return il.import_module(filename)


def get_schemas_dag_file(_module):
    contents = {k: getattr(_module, k) for k in schemas}
    return contents


def get_all_schemas():
    apps = get_new_apps()
    if len(apps):
        print("Found the following apps: {}".format([app.name for app in apps]))
    else:
        print("No apps were found to update")
    schemas_new = {app.name: app.get_schemas() for app in apps}
    print("Found the following new apps: {}".format([app.name for app in apps]))
    return schemas_new


def update_schemas(**kwargs):
    schemas = get_all_schemas()
    # we update all schemas that we found:
    for key, value in schemas.items():
        Variable.set(key=key, value=value, serialize_json=True)


dag = DAG(
    "update_all_schemas", default_args=default_args, catchup=False, tags=["internal"]
)

update_schema2 = PythonOperator(
    task_id="update_all_schemas",
    provide_context=True,
    python_callable=update_schemas,
    dag=dag,
)


if __name__ == "__main__":
    update_schemas()
