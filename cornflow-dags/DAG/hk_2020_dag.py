from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
import cornflow_client.airflow.dag_utilities as utils
from hackathonbaobab2020 import get_solver, Instance
from hackathonbaobab2020.tests import get_test_instance

# This needs to remain to we can get the instance and solution schemas from outside
from hackathonbaobab2020.schemas import instance, solution, config

from timeit import default_timer as timer


name = 'hk_2020_dag'
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)


def solve(data, config):
    """
    :param data: json for the problem
    :param config: execution configuration, including solver
    :return: solution and log
    """
    print("Solving the model")
    solver = config.get('solver', 'default')
    solver_class = get_solver(name=solver)
    if solver_class is None:
        raise utils.NoSolverException("Solver {} is not available".format(solver))
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

    log = dict()
    sol = None
    if status != 0:
        # export everything:
        status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
        log = dict(time=timer() - start, solver=solver, status=status_conv.get(status, "Unknown"))
        if status in [2, 4]:
            sol = algo.solution.to_dict()
    return sol, "", log


def solve_hk(**kwargs):
    return utils.cf_solve(fun=solve, dag_name=name, secrets=EnvironmentVariablesBackend(), **kwargs)


def test_cases():
    options = [('j10.mm.zip', 'j102_4.mm'), ('j10.mm.zip', 'j102_5.mm'), ('j10.mm.zip', 'j102_6.mm')]
    return [get_test_instance(*op).to_dict() for op in options]


hackathon_task = PythonOperator(
    task_id='hk_2020_dag',
    python_callable=solve_hk,
    dag=dag
)
