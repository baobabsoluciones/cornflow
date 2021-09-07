from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.secrets.environment_variables import EnvironmentVariablesBackend
import cornflow_client.airflow.dag_utilities as utils
from cornflow_client import get_empty_schema
from ortools.sat.python import cp_model
import pytups as pt
import os
from timeit import default_timer as timer
import json


name = "graph_coloring"
dag = DAG(name, default_args=utils.default_args, schedule_interval=None)
with open(os.path.join(os.path.dirname(__file__), "input.json"), "r") as f:
    instance = json.load(f)
with open(os.path.join(os.path.dirname(__file__), "output.json"), "r") as f:
    solution = json.load(f)
config = get_empty_schema()
config["properties"] = dict(timeLimit=dict(type="number"))


def solve(data, config):
    """
    :param data: json for the problem
    :param config: execution configuration, including solver
    :return: solution and log
    """
    start = timer()
    model = cp_model.CpModel()
    input_data = pt.SuperDict.from_dict(data)
    pairs = input_data["pairs"]
    n1s = pt.TupList(pairs).vapply(lambda v: v["n1"])
    n2s = pt.TupList(pairs).vapply(lambda v: v["n2"])
    nodes = (n1s + n2s).unique2()
    max_colors = len(nodes) - 1

    # variable declaration:
    color = pt.SuperDict(
        {
            node: model.NewIntVar(0, max_colors, "color_{}".format(node))
            for node in nodes
        }
    )
    for pair in pairs:
        model.Add(color[pair["n1"]] != color[pair["n2"]])
        # model.AddAllDifferent(color[n] for n in nodes)

    # TODO: identify maximum cliques and apply constraint on the cliques instead of on pairs

    obj_var = model.NewIntVar(0, max_colors, "total_colors")
    model.AddMaxEquality(obj_var, color.values())
    model.Minimize(obj_var)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.get("timeLimit", 10)
    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return status
    color_sol = color.vapply(solver.Value)

    assign_list = color_sol.items_tl().vapply(lambda v: dict(node=v[0], color=v[1]))
    solution = dict(assignment=assign_list)
    status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
    log = dict(
        time=timer() - start,
        solver="ortools",
        status=status_conv.get(status, "Unknown"),
    )
    return solution, "", log


def solve_hk(**kwargs):
    return utils.cf_solve(solve, name, EnvironmentVariablesBackend(), **kwargs)


def test_cases():
    file_dir = os.path.join(os.path.dirname(__file__), "data")
    files = os.listdir(file_dir)
    test_files = pt.TupList(files).vfilter(lambda v: v.startswith("gc_"))
    return [read_file(os.path.join(file_dir, fileName)) for fileName in test_files]


def read_file(filePath):
    with open(filePath, "r") as f:
        contents = f.read().splitlines()

    pairs = (
        pt.TupList(contents[1:])
        .vapply(lambda v: v.split(" "))
        .vapply(lambda v: dict(n1=int(v[0]), n2=int(v[1])))
    )
    return dict(pairs=pairs)


graph_coloring = PythonOperator(task_id=name, python_callable=solve_hk, dag=dag)
