from airflow import DAG
from airflow.operators.python import PythonOperator

from datetime import datetime, timedelta
from utils import cf_solve
import pulp as pl
import orloge as ol
import os
from utils import NoSolverException

default_args = {
    'owner': 'baobab',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}
dag_name = 'solve_model_dag'
dag = DAG(dag_name, default_args=default_args, schedule_interval=None)


def solve_model(data, config):
    """
    :param data: pulp json for the model
    :param config: pulp config for solver
    :return:
    """
    print("Solving the model")
    var, model = pl.LpProblem.from_dict(data)

    # we overwrite the logPath argument before solving.
    log_path = config['logPath'] = 'temp.log'
    config['msg'] = 0
    try:
        solver = pl.getSolverFromDict(config)
    except pl.PulpSolverError:
        raise NoSolverException("Missing solver attribute")
    if solver is None or not solver.available():
        raise NoSolverException("Solver {} is not available".format(solver))
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
        try:
            log_dict = ol.get_info_solver(path=log, solver=solver_name, get_progress=True, content=True)
        except:
            log_dict = dict()
        else:
            log_dict['progress'] = log_dict['progress'].fillna('').to_dict(orient='list')
    print("Log read")

    try:
        os.remove(log_path)
    except:
        pass

    return solution, log, log_dict


def run_solve(**kwargs):
    return cf_solve(solve_model, dag_name, **kwargs)


solve_task = PythonOperator(
    task_id='solve_task',
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)
