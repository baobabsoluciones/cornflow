import cornflow_client.airflow.dag_utilities as utils
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
from cornflow_client import get_pulp_jsonschema

from .instance import Instance
from .model import Algorithm
from .modelClosestNeighbor import Algorithm as Heuristic
from .model_ortools import Algorithm as ORT_Algorithm
from .solution import Solution
from .tools import load_json

name = "vrp"
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)
instance = Instance.get_schema()
solution = Solution.get_schema()

# this is the configuration part.
# we will assign the solver options that we later use in get_solver
solvers = dict(algorithm1=Algorithm, algorithm2=Heuristic, algorithm3=ORT_Algorithm)
solver_keys = list(solvers.keys())
config = get_pulp_jsonschema("solver_config.json")
config["properties"]["solver"]["enum"] = solver_keys
config["properties"]["solver"]["default"] = solver_keys[0]


def get_solver(solver):
    options = solvers
    return options.get(solver, Heuristic)


def test_cases():
    data = load_json("input_test_1.json")
    return [data]


def solve(data, config):
    solver_name = config.get("solver")
    solver_obj = get_solver(solver_name)
    solver = solver_obj(Instance.from_dict(data))
    solver.solve(config)
    return solver.solution.to_dict(), "", dict()


def run_solve(**kwargs):
    return utils.cf_solve(
        fun=solve, dag_name=name, secrets=EnvironmentVariablesBackend(), **kwargs
    )


vrp = PythonOperator(task_id=name, python_callable=run_solve, dag=dag)
