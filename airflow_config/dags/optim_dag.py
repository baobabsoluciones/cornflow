from airflow import DAG
from airflow.operators import BashOperator, PythonOperator
from datetime import datetime, timedelta
from api_functions import login, get_data, write_solution
import pulp as pl

# Following are defaults which can be overridden later on
default_args = {
    'owner': 'hugo',
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

"""
Functions
"""


def get_arg(arg, context):
    print(context)
    return context["dag_run"].conf[arg]


def solve_model(data, config):
    print("Solving the model")
    var, model = pl.LpProblem.from_dict(data)
    print(config)
    solver = pl.get_solver_from_dict(config)
    model.solve(solver)
    solution = model.to_dict()

    log_path = config["logPath"]
    f = open(log_path, "r")
    log = f.read()

    print("Model solved")

    return solution, log


def solve_execution(token, execution_id):
    execution_data = get_data(token, execution_id)
    solution, log = solve_model(execution_data["data"], execution_data["config"])
    write_solution(token, execution_id, solution, log)

    return solution


def run_solve(**kwargs):
    token = login(email="airflow@noemail.com", pwd="airflow")
    exec_id = get_arg("exec_id", kwargs)
    print("starting to solve the model with execution %s" % exec_id)
    data = get_data(token, exec_id)
    solution = solve_execution(token, exec_id)

    if solution:
        return "Solution saved"
    else:
        return "Error in writing"


def check_db(**kwargs):
    print("Check if the execution id exist")
    exec_id = get_arg("exec_id", kwargs)
    
    id_in_db = True
    
    if id_in_db:
        return "Execution id exist"
    else:
        raise Exception("Execution id does not exist")


check_db_task = PythonOperator(
    task_id='task_0',
    provide_context=True,
    python_callable=check_db,
    dag=dag,
)

solve_task = PythonOperator(
    task_id='task_1',
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)

solve_task.set_upstream(check_db_task)

