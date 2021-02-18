from airflow import DAG, AirflowException
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
import json
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
    'schedule_interval': "@hourly"
}


def update_schemas(**kwargs):
    _dir = os.path.dirname(__file__)
    schemas = [f for f in os.listdir(_dir) if os.path.splitext(f)[1] == '.json']
    print("Found the following schemas: {}".format(schemas))
    for schema in schemas:
        with open(os.path.join(_dir, schema), 'r') as f:
            content = json.load(f)
        name = os.path.splitext(schema)[0]
        Variable.set(key=name, value=content, serialize_json=True)


dag = DAG('update_all_schemas', default_args=default_args, catchup=False)

update_schema2 = PythonOperator(
    task_id='update_all_schemas',
    provide_context=True,
    python_callable=update_schemas,
    dag=dag,
)
