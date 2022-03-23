Cornflow-dags
===============

Public DAGs for cornflow server

Uploading a new app / solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setting the environment
------------------------

This project requires python 3.5 or above::

    python -m venv venv
    venv/Scripts/activate
    pip install -r requirements.txt

Introduction
-------------

There are several things that are needed when submitting a new solver.

1. a `solve` function.
2. a `name` string.
3. an `instance` dictionary.
4. an `solution` dictionary.
5. a `test_cases` function that returns a list of dictionaries.

In its most minimalistic form: an app constitutes one dag file that contains all of this.
In the following lines we will explain each of these concepts while using the graph-coloring example dag. This example can be found in the `DAG/graph_coloring` directory.

The solver
------------

The solver comes in the form of a python function that takes exactly two arguments: `data` and `config`. The first one is a python dictionary with the input data to solve the problem. The second one is also a dictionary with the execution configuration.

This function needs to be named `solve` and returns three things: a python dictionary with the output data, a string that stores the whole log, and a dictionary with the log information processed. Only the first needs to have a value.

The function for the graph-coloring case is::

    from ortools.sat.python import cp_model
    import pytups as pt
    from timeit import default_timer as timer


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
        log = ""
        status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
        log = dict(
            time=timer() - start,
            solver="ortools",
            status=status_conv.get(status, "Unknown"),
        )
        return solution, "", log

Name and configuration
-----------------------

You need to choose a name for the solution method, as well as the configuration schema. A quick way of creating a configuration is just creating an empty schema and add some parameters. In the graph-coloring example we add a `timeLimit` property to stop the solver after X seconds::

    name = "graph_coloring"
    config = get_empty_schema()
    config["properties"] = dict(timeLimit=dict(type="number"))

The input schema and output schema
-----------------------------------------

Both schemas are built and deployed similarly so we present how the input schema is done.

The input schema is a json schema file (https://json-schema.org/) that includes all the characteristics of the input data for each dag. This file can be built with many tools (a regular text editor could be enough).

In order to upload it, you need to have an `instance` variable available in your dag file.

In the case of the graph-coloring, these variables are imported from the package::

    with open(os.path.join(os.path.dirname(__file__), "input.json"), "r") as f:
        instance = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), "output.json"), "r") as f:
        solution = json.load(f)

This just imports the `input.json` and `output.json` files as python dictionaries. You can check either file to see how they are structured.

Airflow functions and name
-----------------------------
There are some basic functions and declarations that need to be created. The easiest is to just copy the ones from and example and adapt them if needed::

    from airflow import DAG
    from airflow.operators.python import PythonOperator
    import cornflow_client.airflow.dag_utilities as utils

    dag = DAG(name, default_args=utils.default_args, schedule_interval=None)
    def solve_hk(**kwargs):
        return utils.cf_solve(solve, name, EnvironmentVariablesBackend(), **kwargs)

    graph_coloring = PythonOperator(task_id=name, python_callable=solve_hk, dag=dag)


Unit tests
------------

The `test_cases` function is used in the unittests to be sure the solver works as intended. In the graph-coloring example we read the examples from the the `data` directory and transform them to the correct format::

    def test_cases():
        file_dir = os.path.join(os.path.dirname(__file__), "..", "data")
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

To be sure that the the the solution method is tested, you need to edit the `tests/test_dags.py` file and add a reference to your solver::

    class GraphColor(BaseDAGTests.SolvingTests):
        def setUp(self):
            super().setUp()
            self.app = _import_file("graph_coloring")

Then, you can execute the unittests for your solver with the following command::

    python -m unittest tests.test_dags.GraphColor
