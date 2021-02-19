from airflow import DAG
from airflow.operators.python import PythonOperator

from datetime import datetime, timedelta
from utils import cf_solve, NoSolverException
from hackathonbaobab2020 import get_solver, Instance
from hackathonbaobab2020.core.tools import dict_to_list

from timeit import default_timer as timer

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

dag_name = 'hk_2020_dag'
dag = DAG(dag_name, default_args=default_args, schedule_interval=None)


def solve_from_dict(data, config):
    """
    :param data: json for the problem
    :param config: execution configuration, including solver
    :return: solution and log
    """
    print("Solving the model")
    solver = config.get('solver')
    solver_class = get_solver(name=solver)
    if solver_class is None:
        raise NoSolverException("Solver {} is not available".format(solver))
    inst = Instance.from_dict(data)
    algo = solver_class(inst)
    start = timer()

    try:
        status = algo.solve(config)
        print("ok")
    except Exception as e:
        print("problem was not solved")
        print(e)
        status = 0

    if status != 0:
        # export everything:
        status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
        log = dict(time=timer() - start, solver=solver, status=status_conv.get(status, "Unknown"))
        sol = dict_to_list(algo.solution.data, 'job')
    else:
        log = dict()
        sol = {}
    return sol, "", log


def solve_hk(**kwargs):
    return cf_solve(solve_from_dict, dag_name, **kwargs)


hackathon_task = PythonOperator(
    task_id='hk_2020_task',
    python_callable=solve_hk,
    dag=dag
)
