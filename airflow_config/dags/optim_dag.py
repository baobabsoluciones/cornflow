from airflow import DAG
from airflow.operators import BashOperator, PythonOperator
from datetime import datetime, timedelta
from cornflow_client import CornFlow
import pulp as pl
import orloge as ol
import os
import json

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
    return context["dag_run"].conf[arg]


def solve_model(data, config):
    """
    :param data: pulp json for the model
    :param config: pulp config for solver
    :return:
    """
    print("Solving the model")
    var, model = pl.LpProblem.from_dict(data)
    print(config)

    # we overwrite the logPath argument before solving.
    log_path = config['logPath'] = 'temp.log'
    solver = pl.get_solver_from_dict(config)
    model.solve(solver)
    solution = model.to_dict()

    print("Model solved")

    with open(log_path, "r") as f:
        log = f.read()

    # we convert the log into orloge json
    equivs = \
        dict(
            CPLEX_CMD='CPLEX', CPLEX_PY='CPLEX', CPLEX_DLL='CPLEX',
            GUROBI='GUROBI', GUROBI_CMD='GUROBI',
            PULP_CBC_CMD='CBC', COIN_CMD='CBC'
        )
    solver_name = equivs.get(solver.name)
    log_dict = None
    if solver_name:
        log_dict = ol.get_info_solver(path=log, solver=solver_name, get_progress=False, content=True)
        log_dict['progress'] = None
    print("Log read")

    try:
        os.remove(log_path)
    except:
        pass

    return solution, log, log_dict

def run_solve(**kwargs):
    exec_id = get_arg("exec_id", kwargs)
    cornflow_url = get_arg("cornflow_url", kwargs)
    airflow_user = CornFlow(url=cornflow_url)

    # login
    airflow_user.login(email="airflow@baobabsoluciones.es", pwd="THISNEEDSTOBECHANGED")
    print("starting to solve the model with execution %s" % exec_id)
    # get data
    execution_data = airflow_user.get_data(exec_id)
    # solve model
    solution, log, log_dict = solve_model(execution_data["data"], execution_data["config"])
    # write solution
    airflow_user.write_solution(exec_id, solution, log_text=log, log_json=log_dict)
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



solve_task = PythonOperator(
    task_id='solve_task',
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)

