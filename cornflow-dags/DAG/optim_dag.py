from airflow import DAG
from airflow.operators.python import PythonOperator

try:
    import utils
except ImportError:
    import DAG.utils as utils

import pulp as pl
import orloge as ol
import os


name = 'solve_model_dag'
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)
instance, solution = utils.get_schemas_from_file(name)


def solve(data, config):
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
    if 'solver' not in config:
        config['solver'] = 'PULP_CBC_CMD'
    try:
        solver = pl.getSolverFromDict(config)
    except pl.PulpSolverError:
        raise utils.NoSolverException("Missing solver attribute")
    if solver is None or not solver.available():
        raise utils.NoSolverException("Solver {} is not available".format(solver))
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
    return utils.cf_solve(solve, name, **kwargs)


def test_cases():
    prob = pl.LpProblem("test_export_dict_MIP", pl.LpMinimize)
    x = pl.LpVariable("x", 0, 4)
    y = pl.LpVariable("y", -1, 1)
    z = pl.LpVariable("z", 0, None, pl.LpInteger)
    prob += x + 4 * y + 9 * z, "obj"
    prob += x + y <= 5, "c1"
    prob += x + z >= 10, "c2"
    prob += -y + z == 7.5, "c3"
    return [prob.toDict()]


solve_task = PythonOperator(
    task_id='solve_model_dag',
    provide_context=True,
    python_callable=run_solve,
    dag=dag,
)
