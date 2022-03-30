Introduction
==========================


Cornflow is a collection of projects that allow for the rapid prototyping and deployment of optimization-based applications. Contrary to other existing deployment servers, Cornflow is centered around the applications and the problems, not in the techniques. It offers several other advantages such as being completely free (as in freedom) and very flexible.

Cornflow uses input and output schemas to define “optimization problems” and then accepts any (for now python) code that reads data in the input schema and returns a solution in the output schema. We use JSONSchema to define these schemas. By working like this, Cornflow becomes technique-agnostic without losing data-validation and re-usability (e.g., we can have more than one “solution method” for the same problem).

Being technique-agnostic implies we sometimes use CP models built with ortools, MIP models built with pyomo and some heuristics in pure python. But again, we could also have a localsolver model or any metaheuristic as long as it complies with the interface format for the particular optimization problem. In the :ref:`Examples of solution methods` section we describe some of the demo solution methods we have built and deployed.


Ways it can be used
---------------------

Cornflow main advantage is its flexibility and so it can be used and deployed in many ways. The easiest is to use the test server we already have deployed to test the current offer of solvers. For this, check the :ref:`User your solution method` section on how to test the server and then the :ref:`Examples of solution methods` section to see what solvers are available.

If you want to have your solution available in the server, feel free to propose a new solution method via a Pull Request. This is explained in section :ref:`How to deploy a new solution method (2.0)`.

Finally, if you want to deploy your own Cornflow-server privately and deploy your own private solution methods, you can check the several ways in which you can do that in :ref:`Deploy your own Cornflow-server`.
