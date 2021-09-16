How to deploy a new solution method (2.0)
===================================================

The deployment of a solution method consists of sub-classing the class :py:class:`cornflow_client.core.application.ApplicationCore` from the package ``cornflow_client``. ``ApplicationCore`` serves as a template for apps and requires certain properties and methods to be defined.

We will use as example the TSP problem defined here. At the end of the document, the complete code with all imports is available.

Application
---------------

First, we make a subclass of `ApplicationCore`:

.. code-block:: python

    class TspApp(ApplicationCore):
        name = "tsp"
        instance = Instance
        solution = Solution
        solvers = dict(naive=TSPNaive)
        schema = load_json(os.path.dirname(__file__), "config.json")

        @property
        def test_cases(self) -> List[Dict]:
            return []

As you can see, we have given the application a class name (and a name property). We also have passed several other properties: instance, solution, solvers and schema. Finally, we have created a ``test_cases`` property.

We will go over each of the required properties.

Instance class
---------------

This is just a subclass of :py:class:`cornflow_client.core.instance.InstanceCore`. There are many default methods that can be overwritten (``to_dict``, ``from_dict``, etc.). The only required property is the ``schema``. Here we have just imported a file with the corresponding json-schema. If you want to know how to define a json-schema, check the section :ref:`Write a json-schema`.

.. code-block:: python

    class Instance(InstanceCore):
        schema = load_json(os.path.dirname(__file__), "input.json")


Solution class
---------------

Very similar to the Instance. The Solution is just a subclass of :py:class:`cornflow_client.core.solution.SolutionCore`.

.. code-block:: python

    class Solution(SolutionCore):
        schema = load_json(os.path.dirname(__file__), "output.json")


Solution method / solvers class
------------------------------------

The solution method is a subclass of :py:class:`cornflow_client.core.experiment.ExperimentCore` and should define three methods: ``solve``, ``get_objective`` and ``check_solution``. Here is the implementation of a very very bad solution method for the TSP:

.. code-block:: python

    class TSPNaive(ExperimentCore):
        def solve(self, options: dict):
            # we just get an arbitrary but complete list of nodes and we return it
            nodes = (
                TupList(v["n1"] for v in self.instance.data["arcs"])
                .unique()
                .kvapply(lambda k, v: dict(pos=k, node=v))
            )
            self.solution = Solution(dict(route=nodes))
            return {}

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


More than one solution method can be defined. This is why they are given in a dictionary to the Application. We use them as a catalogue when deciding to solve a problem.

Test cases property
------------------------------------

Test cases is a property that should return a list of datasets (in json-schema format). These tests are used to test the app in the unit-tests. More information on how to create the unit tests for your solution method in :ref:`Test your solution method`.


Schema property
------------------

The schema of an application is the configuration used to solve a problem. This schema needs to have at least the `timeLimit` and the `solver` properties. Besides that, it's up to the developer to decide which configuration is needed. If you want to know how to define a json-schema, check the section :ref:`Write a json-schema`.


Code structure
------------------------------------

Each app is contained ideally inside a directory. Usually, the ``Instance``, ``Solution`` and ``Solution method`` are located each one inside a separate file. The ``__init__.py`` needs to contain the Application class. Other files inside the folder include the schemas (better stored as json files).

In this example we put everything inside the ``__init__.py`` except the json-schema files because it was a small example.


Complete __init__.py code for the TSP
----------------------------------------

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
    from DAG.tools import load_json


    class Instance(InstanceCore):
        schema = load_json(os.path.dirname(__file__), "input.json")


    class Solution(SolutionCore):
        schema = load_json(os.path.dirname(__file__), "output.json")


    class TSPNaive(ExperimentCore):
        def solve(self, options: dict):
            # we just get an arbitrary but complete list of nodes and we return it
            nodes = (
                TupList(v["n1"] for v in self.instance.data["arcs"])
                .unique()
                .kvapply(lambda k, v: dict(pos=k, node=v))
            )
            self.solution = Solution(dict(route=nodes))
            return {}

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


    class TspApp(ApplicationCore):
        name = "tsp"
        instance = Instance
        solution = Solution
        solvers = dict(naive=TSPNaive)
        schema = load_json(os.path.dirname(__file__), "config.json")

        @property
        def test_cases(self) -> List[Dict]:
            return []
