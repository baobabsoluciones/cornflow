from airflow import DAG, AirflowException
from airflow.operators.python_operator import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from cornflow_client import CornFlow, CornFlowApiError
from datetime import datetime, timedelta
import model_functions as mf
from urllib.parse import urlparse


# Following are defaults which can be overridden later on
# TODO: clean this
default_args = {
    'owner': 'baobab',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}

dag = DAG('solve_model_dag', default_args=default_args, schedule_interval=None)


def get_arg(arg, context):
    return context["dag_run"].conf[arg]


def try_to_save_error(client, exec_id):
    try:
        client.put_api_for_id('dag/', id=exec_id, payload=dict(state=-6))
    except Exception as e:
        print("An exception trying to register the failed status: {}".format(e))


def run_solve(**kwargs):
    exec_id = get_arg("exec_id", kwargs)

    # This secret comes from airflow configuration
    secrets = EnvironmentVariablesBackend()
    uri = secrets.get_conn_uri('CF_URI')
    conn = urlparse(uri)

    # TODO: what if https??
    airflow_user = CornFlow(url="http://{}:{}".format(conn.hostname, conn.port))

    # login
    airflow_user.login(email=conn.username, pwd=conn.password)
    print("starting to solve the model with execution %s" % exec_id)
    # get data
    execution_data = airflow_user.get_data(exec_id)
    # solve model
    try:
        solution, log, log_dict = mf.solve_model(execution_data["data"], execution_data["config"])
    except mf.NoSolverException:
        try_to_save_error(airflow_user, exec_id)
        raise AirflowException('No solver found')
    except:
        try_to_save_error(airflow_user, exec_id)
        raise AirflowException('Unknown error')
    # write solution
    try:
        airflow_user.write_solution(exec_id, solution, log_text=log, log_json=log_dict)
    except CornFlowApiError:
        try_to_save_error(airflow_user, exec_id)
        # attempt to update the execution with a failed status.
        raise AirflowException('The writing of the solution failed')

    if solution:
        return "Solution saved"


solve_task = PythonOperator(
    task_id='solve_task',
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)
