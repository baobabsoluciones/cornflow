from airflow import DAG
from airflow.operators.python import PythonOperator

try:
    import utils
except ImportError:
    import DAG.utils as utils

from ortools.sat.python import cp_model
import pytups as pt
import os
from timeit import default_timer as timer


name = 'graph_coloring'
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)
instance, solution = utils.get_schemas_from_file(name)


def solve(data, config):
    """
    :param data: json for the problem
    :param config: execution configuration, including solver
    :return: solution and log
    """
    start = timer()
    model = cp_model.CpModel()
    input_data = pt.SuperDict.from_dict(data)
    nodes = input_data['nodes']
    pairs = input_data['pairs']
    max_colors = len(nodes) - 1

    # variable declaration:
    color = pt.SuperDict({node: model.NewIntVar(0, max_colors, 'color_{}'.format(node)) for node in nodes})
    for pair in pairs:
        model.Add(color[pair['n1']] != color[pair['n2']])
        # model.AddAllDifferent(color[n] for n in nodes)

    # TODO: identify maximum cliques and apply constraint on the cliques instead of on pairs

    obj_var = model.NewIntVar(0, max_colors, 'total_colors')
    model.AddMaxEquality(obj_var, color.values())
    model.Minimize(obj_var)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.get('timeLimit', 10)
    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return status
    color_sol = color.vapply(solver.Value)

    assign_list = color_sol.items_tl().vapply(lambda v: dict(node=v[0], color=v[1]))
    solution = dict(assignment=assign_list)
    log = ""
    status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
    log = dict(time=timer() - start, solver='ortools', status=status_conv.get(status, "Unknown"))
    return solution, "", log


def solve_hk(**kwargs):
    return utils.cf_solve(solve, name, **kwargs)


def test_cases():
    file_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    files = os.listdir(file_dir)
    test_files = pt.TupList(files).vfilter(lambda v: v.startswith('gc_'))
    return [read_file(os.path.join(file_dir, fileName)) for fileName in test_files]


def read_file(filePath):
    with open(filePath, 'r') as f:
        contents = f.read().splitlines()

    pairs = \
        pt.TupList(contents[1:]).\
        vapply(lambda v: v.split(' ')). \
        vapply(lambda v: dict(n1=int(v[0]), n2=int(v[1])))
        # vapply(lambda v: [int(v[0]), int(v[1])])
    num_nodes, num_pairs = [int(a) for a in contents[0].split(' ')]
    nodes = range(num_nodes)
    return dict(nodes=list(nodes), pairs=pairs)


graph_coloring = PythonOperator(
    task_id='graph_coloring',
    python_callable=solve_hk,
    dag=dag
)

