import cornflow_client.airflow.dag_utilities as utils
from airflow.operators.python import PythonOperator
from airflow import DAG
from timeit import default_timer as timer
import os
from .schemas import instance_schema, solution_schema, config_schema
from .core import Instance
from .DirectHeuristic import DirectHeuristic
from .DynamicSolver import DynamicSolver
from .RandomHeuristic import RandomHeuristic
from .parameters import threshold


name = "knapsack"
instance = instance_schema
solution = solution_schema
config = config_schema

solvers = dict(Dynamic=DynamicSolver, Direct=DirectHeuristic, Random=RandomHeuristic)


def get_solver(data, conf):
    solver_name = conf.get("solver", "Direct")
    if (
        data["parameters"]["nb_objects"] * data["parameters"]["weight_capacity"]
        > threshold
        and solver_name == "Dynamic"
    ):
        solver_name = "Direct"
    solver_cls = solvers.get(solver_name)
    return solver_cls


def solve(data, conf):
    start = timer()

    solver_cls = get_solver(data, conf)

    model = solver_cls(Instance.from_dict(data))
    status = model.solve(conf)

    time = timer() - start
    log = model.log
    log += f"Computation time :{time}s, Solver used : {model.solver}"
    return model.solution.to_dict(), log, dict(time=time, solver=model.solver)


def test_cases():
    cwd = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(cwd, "Data", "ks_4_0")

    data = Instance.from_file(path).to_dict()
    return [data]


dag = DAG(name, default_args=utils.default_args, schedule_interval=None)

knapsack = PythonOperator(
    task_id=name,
    python_callable=solve,
    dag=dag,
)
