from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
import importlib as il
import os


default_args = {
    'owner': 'baobab',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': -1,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': "@hourly",
    "catchup": False,
}

schemas = [('instance', '_input'), ('solution', '_output')]


def get_all_apps():
    _dir = os.path.dirname(__file__)
    print("looking for apps in dir={}".format(_dir))
    print("Files are: {}".format(os.listdir(_dir)))
    files = os.listdir(_dir)
    return [_import_file(os.path.splitext(f)[0]) for f in files if is_app(f)]


def _import_file(filename):
    return il.import_module(filename)


def is_app(dag_module):
    filename, ext = os.path.splitext(dag_module)
    if ext != '.py':
        return False
    try:
        _module = _import_file(filename)
        _module.name
        _module.instance
        return True
    except Exception as e:
        return False


def get_schemas_dag_file(_module):
    contents = [
        (_module.name + tail, getattr(_module, attribute))
        for attribute, tail in schemas
    ]
    return contents


def get_all_schemas():
    apps = get_all_apps()
    names = [app.name for app in apps]
    if len(apps):
        print("Found the following apps: {}".format(names))
    else:
        print("No apps were found to update")
    schemas = []
    for dag_module in apps:
        schemas.extend(get_schemas_dag_file(dag_module))
    return schemas


def update_schemas(**kwargs):
    schemas = get_all_schemas()
    for key, value in schemas:
        Variable.set(key=key, value=value, serialize_json=True)


dag = DAG('update_all_schemas', default_args=default_args, catchup=False)

update_schema2 = PythonOperator(
    task_id='update_all_schemas',
    provide_context=True,
    python_callable=update_schemas,
    dag=dag,
)


if __name__ == '__main__':
    update_schemas()