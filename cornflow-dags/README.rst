===============
Cornflow-dags
===============

Public DAGs for cornflow server

Setting the environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This project requires python 3.7 or above::

    python -m venv venv
    venv/Scripts/activate
    pip install -r requirements.txt
    pip install -U ../libs/client

Optionally, to generate reports, it is required to install quarto: https://quarto.org/docs/download/.

Testing
~~~~~~~~~~~~~~~~~~~~~

To run all tests you may want to do the following::

    python -m unittest tests.test_dags

To run the specific tests for one of the apps, just choose the name of the DAG (example: Tsp)::

    python -m unittest tests.test_dags.Tsp

Running an app
~~~~~~~~~~~~~~~~~~~~~

from python (example with GraphColoring)::

    from DAG.graph_coloring import GraphColoring

    app = GraphColoring()
    # we load an example dataset:
    tests = app.get_unittest_cases()
    instance_data = tests[0].get("instance")
    # we instantiate the instance
    instance = app.instance.from_dict(instance_data)
    # we get the default solver (solvers available in app.solvers)
    s = app.get_default_solver_name()
    my_experim = app.get_solver(s)(instance, None)
    # we solve the problem
    my_experim.solve(dict())
    # the solution is stored in solution:
    my_experim.solution.to_dict()
    # some apps allow generating an html report (Quarto required)
    path_to_report = my_experim.generate_report()


Uploading a new app / solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Introduction
-------------

There are several things that are needed when submitting a new solver.

1. an `Instance` class.
2. a `Solution` class.
3. an `Experiment class`
4. a `Solver` class
5. an `Application class`

A few recommended additions:

1. unit tests.
2. a report.

In its most minimalistic form: an app constitutes one file that contains all of this.
In the following lines we will explain each of these concepts while using the graph-coloring example dag. This example can be found in the `DAG/graph_coloring` directory.

The Instance class
-----------------------------------------
The Instance class is used to process the input data.
It inherits the class `InstanceCore`, that can be found in cornflow_client.core.

In its most basic form, the Instance class should contain at least two fields: schema, and schema_checks.
Those fields should contain the jsonschema used to verify the format of the input data and the input data checks.

In the case of the graph-coloring, the class is defined as::

    import os
    from cornflow_client import InstanceCore, get_empty_schema
    from cornflow_client.core.tools import load_json
    import pytups as pt


    class Instance(InstanceCore):
        schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
        schema_checks = get_empty_schema()

        def get_pairs(self):
            return pt.TupList((el["n1"], el["n2"]) for el in self.data["pairs"])

The class can also define a check() method, that should execute verifications on the input data and return a
dictionary with the errors.
If it defined, this method will be ran before every execution of the solver, to check that the
input data doesn't contain infeasibilities.

From this class, the input data can be accessed through the `data` field.

The Solution class
-----------------------------------------
The Solution class is used to process the output data.
It inherits the class `SolutionCore`, that can be found in cornflow_client.core.

In its most basic form, the Solution class should contain at least one field: schema.
This fields should contain the jsonschema used to verify the format of the output data.

In the case of the graph-coloring, the class is defined as::

    import os
    from cornflow_client import SolutionCore
    from cornflow_client.core.tools import load_json
    import pytups as pt


    class Solution(SolutionCore):
        schema = load_json(
            os.path.join(os.path.dirname(__file__), "../schemas/output.json")
        )

        def get_assignments(self):
            return pt.SuperDict({v["node"]: v["color"] for v in self.data["assignment"]})


From this class, the input data can be accessed through the `data` field.

The Experiment class
-----------------------------------------
The Experiment class is used to work on the union of input and output_data.
It inherits the class `ExperimentCore`, that can be found in cornflow_client.core.
An Experiment object is linked to an Instance and a Solution object and can therefore use their data.

In its most basic form, the Experiment class should contain at least one field and two methods:
schema_checks, get_objective(), check_solution().
The method check_solution() should execute verifications on the output data and return a
dictionary with the errors. The method get_objective() should calculate and return the value of the
objective function given the current Instance and Solution.
The field schema_checks should contain the jsonschema used to verify the format of the output data.

In the case of the graph-coloring, the class is defined as::

    from cornflow_client import ExperimentCore
    from cornflow_client.core.tools import load_json
    from .instance import Instance
    from .solution import Solution
    import os


    class Experiment(ExperimentCore):
        schema_checks = load_json(
            os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
        )

        @property
        def instance(self) -> Instance:
            return super().instance

        @property
        def solution(self) -> Solution:
            return super().solution

        @solution.setter
        def solution(self, value):
            self._solution = value

        def get_objective(self) -> float:
            return self.solution.get_assignments().values_tl().unique().len()

        def check_solution(self, *args, **kwargs) -> dict:
            # if a pair of nodes have the same colors: that's a problem
            colors = self.solution.get_assignments()
            pairs = self.instance.get_pairs()
            errors = [
                {"n1": n1, "n2": n2} for (n1, n2) in pairs if colors[n1] == colors[n2]
            ]
            return dict(pairs=errors)


From this class, the instance can be accessed through the `instance` field, and the solution can be
accessed through the `solution` field.

The solver
------------

The solver is the part of the app that takes care of the resolution of the problem. An app can contain
several ones.
The solver comes in the form of a python class. It inherits the Experiment class. As such, it is also
linked to an Instance and a Solution object and can therefore use their data.

In its most basic form, the Solver class should contain at least a `solve()` method. This method should
take exactly one argument: a dictionary with the execution configuration. It should return a dictionary
with two keys: `status` and `status_sol`. `status` should contain the status of the execution (optimal,
unbounded, time_limit...) while `status_sol` should return the information of whether the execution
has found a solution or not. The mappings of both these statuses are defined in
cornflow_client.constants.

The class for the graph-coloring case is::

    from ortools.sat.python import cp_model
    from cornflow_client.constants import (
        ORTOOLS_STATUS_MAPPING,
        SOLUTION_STATUS_FEASIBLE,
        SOLUTION_STATUS_INFEASIBLE,
    )
    import pytups as pt
    from ..core import Solution, Experiment

    class OrToolsCP(Experiment):
        def solve(self, options: dict):
            model = cp_model.CpModel()
            input_data = pt.SuperDict.from_dict(self.instance.data)
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

            obj_var = model.NewIntVar(0, max_colors, "total_colors")
            model.AddMaxEquality(obj_var, color.values())
            model.Minimize(obj_var)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = options.get("timeLimit", 10)
            termination_condition = solver.Solve(model)
            if termination_condition not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                return dict(
                    status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                    status_sol=SOLUTION_STATUS_INFEASIBLE
                )
            color_sol = color.vapply(solver.Value)

            assign_list = color_sol.items_tl().vapply(lambda v: dict(node=v[0], color=v[1]))
            self.solution = Solution(dict(assignment=assign_list))

            return dict(
                status=ORTOOLS_STATUS_MAPPING.get(termination_condition),
                status_sol=SOLUTION_STATUS_FEASIBLE
            )

The class can also defined a string field `log`. If it does,
the log will be saved in cornflow at the end of the execution with the solution data, so that it
can be consulted by the user.

The Application
-----------------------

The Application class is the base of the app. It links the different resolution methods and takes care
of the connection with the server.
It inherits the class `ApplicationCore`, that can be found in cornflow_client.core.

An Application should contain several fields:

- a string `name`
- an `instance` object that contains the Instance class defined earlier
- a `solution` object that contains the Solution class defined earlier
- a `solvers` dictionary that contains a mapping to the different solvers defined earlier
- a `schema` object that contains the jsonschema corresponding to the configuration dictionaries.
A quick way of creating a configuration is just creating an empty schema and add some parameters.
In the graph-coloring example we add a `timeLimit` property to stop the solver after X seconds.
- a `test_cases` property that should return a list of test instance datasets.
The `test_cases` function is used in the unittests to be sure the solver works as intended.
In the graph-coloring example we read the examples from the the `data` directory and transform
them to the correct format.

The class for the graph-coloring case is::

    from cornflow_client import get_empty_schema, ApplicationCore
    from typing import List, Dict
    import pytups as pt
    import os

    from .solvers import OrToolsCP
    from .core import Instance, Solution


    class GraphColoring(ApplicationCore):
        name = "graph_coloring"
        instance = Instance
        solution = Solution
        solvers = dict(default=OrToolsCP)
        schema = get_empty_schema(
            properties=dict(timeLimit=dict(type="number")), solvers=list(solvers.keys())
        )

        @property
        def test_cases(self) -> List[Dict]:
            def read_file(filePath):
                with open(filePath, "r") as f:
                    contents = f.read().splitlines()

                pairs = (
                    pt.TupList(contents[1:])
                    .vapply(lambda v: v.split(" "))
                    .vapply(lambda v: dict(n1=int(v[0]), n2=int(v[1])))
                )
                return dict(pairs=pairs)

            file_dir = os.path.join(os.path.dirname(__file__), "data")
            files = os.listdir(file_dir)
            test_files = pt.TupList(files).vfilter(lambda v: v.startswith("gc_"))
            return [read_file(os.path.join(file_dir, fileName)) for fileName in test_files]

The jsonschemas
-----------------------------------------

All jsonschemas are built and deployed similarly so we present how the input schema is done.
A jsonschema is a json schema file (https://json-schema.org/) that includes all the characteristics of the data for each dag.
This file can be built with many tools (a regular text editor could be enough).
You can check the `DAG/graph_coloring/schemas` directory to see how they are structured.

Unit tests
------------

To be sure that the the the solution method is tested, you need to edit the `tests/test_dags.py` file
and add a reference to your solver::

    class GraphColor(BaseDAGTests.SolvingTests):
        def setUp(self):
            super().setUp()
            from DAG.graph_coloring import GraphColoring

            self.app = GraphColoring()
            self.config = dict(msg=False)

Then, you can execute the unittests for your solver with the following command::

    python -m unittest tests.test_dags.GraphColor

The reports
--------------

The generation of reports needs to have the `quarto` app installed in the system.
To download and install quarto, check here: https://quarto.org/docs/download/.

A report is a static/ self-contained view of an Experiment (solved or not).

For example, to generate the `tsp` report, you execute::

    quarto render cornflow-dags/DAG/tsp/report/report.qmd

By default, it uses an example instance. If a new instance is needed, the path to it is required::

   quarto render cornflow-dags/DAG/tsp/report/report.qmd -P file_name:PATH_TO_JSON.json

Developing reports
********************

Quarto reports are easier to create using VS-code with the following extensions: `Python`, `Quarto`, `Jupyter`, `black (Microsoft)`.

VS-code offers an interactive window to execute cells, and automatic re-run of the report by watching for changes.

