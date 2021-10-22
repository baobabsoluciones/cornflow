How to deploy a new solution method (2.0)
===================================================

The deployment of a solution method consists of sub-classing the class :py:class:`cornflow_client.core.application.ApplicationCore` from the package ``cornflow_client``. ``ApplicationCore`` serves as a template for apps and requires certain properties and methods to be defined.

We will use as example the TSP problem defined here. At the end of the document, the complete code with all imports is available.

Application class
-------------------

First, we make a subclass of `ApplicationCore`:

.. code-block:: python

    class TspApp(ApplicationCore):
        name = "tsp"
        instance = Instance
        solution = Solution
        solvers = dict(naive=TSPNaive)
        schema = load_json(os.path.join(os.path.dirname(__file__), "config.json"))

        @property
        def test_cases(self) -> List[Dict]:
            return []

As you can see, we have given the application a class name (and a name property). We also have passed several other properties: instance, solution, solvers and schema. Finally, we have created a ``test_cases`` property.

We will go over each of the required properties below.

Instance class
---------------

This is just a subclass of :py:class:`cornflow_client.core.instance.InstanceCore`. There are many default methods that can be overwritten (``to_dict``, ``from_dict``, etc.). The only required property is the ``schema``. Here we have just imported a file with the corresponding json-schema. If you want to know how to define a json-schema, check the section :ref:`Write a json-schema`.

.. code-block:: python

    class Instance(InstanceCore):
        schema = load_json(os.path.join(os.path.dirname(__file__), "input.json"))


Solution class
---------------

Very similar to the Instance. The Solution is just a subclass of :py:class:`cornflow_client.core.solution.SolutionCore`.

.. code-block:: python

    class Solution(SolutionCore):
        schema = load_json(os.path.join(os.path.dirname(__file__), "output.json"))

Experiment class
-----------------

Although not strictly necessary, it is usually good practice to define an Experiment class that subclasses :py:class:`cornflow_client.core.experiment.ExperimentCore`. This class takes as input an :ref:`Instance class` and a :ref:`Solution class`. Its purpose is to evaluate and validate a given solution. To achieve this, the class should implement at least two methods ``get_objective`` and ``check_solution``.

get_objective
*****************

``get_objective`` returns a scalar number that represents the objective function value of the solution.


check_solution
*****************

``check_solution`` returns a dictionary of dictionaries. Each key in the first dictionary represents a specific validation. Each key in the second dictionary represents the domain of a given validation where the solution violates its requirement. The value of the second dictionary represents the extent of the violation.

In the example below for the TSP, a possible value for ``check_solution()`` could be:

.. code-block:: python

    {
        "missing_nodes": {5: 1, 6: 1}
    }

Which implies that the node 5 and node 6 have not been visited in the solution. The value 1 in this case is not used.


It's important that there should not be more than two dictionary indentation. For example, this would be invalid:

.. code-block:: python

    {
        "missing_nodes": {
            "missing_nodes_1": {5: 1, 6: 1}, 
            "missing_nodes_2": {1: 1, 2: 2},
        }
    }



Example
*****************

.. code-block:: python


    class Experiment(ExperimentCore):
        def get_objective(self) -> float:
            # we get a sorted list of nodes by position
            route = (
                TupList(self.solution.data["route"])
                .sorted(key=lambda v: v["pos"])
                .vapply(lambda v: v["node"])
            )
            weight = {(el["n1"], el["n2"]): el["w"] for el in self.instance.data["arcs"]}
            # we sum all arcs in the solution
            return (
                sum([weight[n1, n2] for n1, n2 in zip(route, route[1:])])
                + weight[route[-1], route[0]]
            )

        def check_solution(self, *args, **kwargs) -> dict:
            nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
            nodes_out = TupList(n["node"] for n in self.solution.data["route"]).to_set()
            missing_nodes = {n: 1 for n in (nodes_in - nodes_out)}
            positions = TupList(n["pos"] for n in self.solution.data["route"]).to_set()
            missing_positions = {p: 1 for p in set(range(len(nodes_in))) - positions}
            return SuperDict(
                missing_nodes=missing_nodes, missing_positions=missing_positions
            )


Solver class
------------------

Each solver is a subclass of the :ref:`Experiment class` and should define one additional method: ``solve``. Here is the implementation of a very very bad solver for the TSP:

.. code-block:: python

    class TSPNaive(Experiment):
        def solve(self, options: dict):
            # we just get an arbitrary but complete list of nodes and we return it
            nodes = (
                TupList(v["n1"] for v in self.instance.data["arcs"])
                .unique()
                .kvapply(lambda k, v: dict(pos=k, node=v))
            )
            self.solution = Solution(dict(route=nodes))
            return {}


More than one solution method can be defined. This is why they are given in a dictionary to the :ref:`Application class`. We use them as a catalogue when deciding to solve a problem.

Test cases
-------------

Test cases is a property that should return a list of datasets (in json-schema format). These tests are used to test the app in the unit-tests. More information on how to create the unit tests for your solution method in :ref:`Test your solution method`.


Schema property
------------------

The schema of an application is the configuration used to solve a problem. This schema needs to have at least the `timeLimit` and the `solver` properties. Besides that, it's up to the developer to decide which configuration is needed. If you want to know how to define a json-schema, check the section :ref:`Write a json-schema`.

Conventions
*****************

We follow some common conventions in the configuration schema so most apps share most of the main properties. Below is a list of known properties and what the usually represent.

#. **timeLimit**: float. It indicates the amount of seconds before the method should stop.
#. **solver**: string. It indicates the solution method that should be used to solve the problem. It can support "nested solvers". For example: ``pulp.cbc`` should be parsed as "using the ``pulp`` solution method and, inside that solution method, use the ``cbc`` solver.
#. **msg**: boolean. When ``true``, the solution method displays details of the progress.
#. **warmStart**: boolean. When ``true``, the solution method will use the current solution (if any) to start the exploration of solutions.
#. **fixSolution**: boolean. When ``true``, the solution method will fix the existing information in the solution when exploring the solution space.
#. **gapAbs**: float. The maximum absolute gap allowed when considering a solution optimal.
#. **gapRel**: float. The maximum relative gap allowed when considering a solution optimal.
#. **threads**: integer. The number of cores that should be used in the solution method.

Cornflow-client has some utility functions to help while making this configuration schema. For small solution methods, it doesn't make much sense to be creating a separated ``config.json`` schema file. For these cases, it's possible to use :py:func:`cornflow_client.schema.tools.get_empty_schema`.

Instance and solution schemas
*******************************

Instance and Solution classes also require their own schemas. See their own sections for more details on how to provide them: :ref:`Instance class` and :ref:`Solution class` respectively.


README
--------------

It is a good idea to have a description of the problem to be solved in text form. Even better if the text is accompanied by a mathematical formulation in LaTeX. This way, others can check the problem description and better understand the input data, output data and the solution methods.


Code structure
------------------------------------

Assuming your solution is called ``my_project``, the following is the official structure to organize an application::

    my_project/
        __init__.py
        README.md
        core/
            __init__.py
            instance.py
            solution.py
            experiment.py
        schemas/
            __init__.py
            instance.json
            solution.json
            config.json
        data/
            data_file_1.json
            data_file_2.json
        solvers/
            __init__.py
            solver_1.py
            solver_2.py

Each app is contained ideally inside a directory.

The :ref:`Instance class` is implemented in the ``my_project/core/instance.py`` file, the :ref:`Solution class` inside the ``my_project/core/solution.py``.

Each :ref:`Solver class` is defined in the ``my_project/solvers`` directory: ``solver_1.py``, ``solver_2.py``, etc.

The :ref:`Application class` is defined inside ``my_project/__init__.py``.

Schemas are stored in the ``my_project/schemas`` folder. Finally, :ref:`Test cases` are stored in the ``my_project/data`` directory.

Complete __init__.py code for the TSP
----------------------------------------

In this example we put everything inside the ``__init__.py`` (except the json-schema files) for simplicity.

.. code-block:: python

    from cornflow_client import (
        ApplicationCore,
        InstanceCore,
        SolutionCore,
        ExperimentCore,
    )
    from pytups import TupList, SuperDict
    import os
    from typing import List, Dict
    from cornflow_client.core.tools import load_json


    class Instance(InstanceCore):
        schema = load_json(os.path.join(os.path.dirname(__file__), "input.json"))


    class Solution(SolutionCore):
        schema = load_json(os.path.join(os.path.dirname(__file__), "output.json"))


    class Experiment(ExperimentCore):
        def get_objective(self) -> float:
            # we get a sorted list of nodes by position
            route = (
                TupList(self.solution.data["route"])
                .sorted(key=lambda v: v["pos"])
                .vapply(lambda v: v["node"])
            )
            weight = {(el["n1"], el["n2"]): el["w"] for el in self.instance.data["arcs"]}
            # we sum all arcs in the solution
            return (
                sum([weight[n1, n2] for n1, n2 in zip(route, route[1:])])
                + weight[route[-1], route[0]]
            )

        def check_solution(self, *args, **kwargs) -> dict:
            nodes_in = TupList(v["n1"] for v in self.instance.data["arcs"]).to_set()
            nodes_out = TupList(n["node"] for n in self.solution.data["route"]).to_set()
            missing_nodes = {n: 1 for n in (nodes_in - nodes_out)}
            positions = TupList(n["pos"] for n in self.solution.data["route"]).to_set()
            missing_positions = {p: 1 for p in set(range(len(nodes_in))) - positions}
            return SuperDict(
                missing_nodes=missing_nodes, missing_positions=missing_positions
            )


    class TSPNaive(Experiment):
        def solve(self, options: dict):
            # we just get an arbitrary but complete list of nodes and we return it
            nodes = (
                TupList(v["n1"] for v in self.instance.data["arcs"])
                .unique()
                .kvapply(lambda k, v: dict(pos=k, node=v))
            )
            self.solution = Solution(dict(route=nodes))
            return {}


    class TspApp(ApplicationCore):
        name = "tsp"
        instance = Instance
        solution = Solution
        solvers = dict(naive=TSPNaive)
        schema = load_json(os.path.join(os.path.dirname(__file__), "config.json"))

        @property
        def test_cases(self) -> List[Dict]:
            return []


Requirements
------------------

The repository contains a file called requirements.txt. You will need to update this file with the name of the additional libraries that your code needs to run.


Pull request
-----------------

Once that all the previous is done, that your code has been pushed to the remote repository, that none of the tests run by git fail (see :ref:`Test your solution method`), and your application seems complete, it is time to merge it into the main branch. Indeed, the dag won’t be running while your code is not on the main branch.

In order to do so, you need to create a pull request on github’s web interface. Once the PR has been approved, your code will be on the main branch.

From there, you will have to wait until the dag is running, which can take a few hours since the running dags are only updated once a day. To learn how to test your app, see :ref:`User your solution method`. To learn to debug your app in the airflow web interface, see :ref:`Debug your solution method`.

