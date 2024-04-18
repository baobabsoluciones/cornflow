.. _introduction-label:

Introduction
============

.. image:: https://img.shields.io/github/actions/workflow/status/baobabsoluciones/cornflow/build_docs.yml?label=docs&logo=github&style=for-the-badge
  :alt: GitHub Workflow Status
  :target: https://github.com/baobabsoluciones/cornflow/actions

.. image:: https://img.shields.io/pypi/v/cornflow?label=cornflow&style=for-the-badge
  :alt: PyPI
  :target: https://pypi.python.org/pypi/cornflow

.. image:: https://img.shields.io/pypi/v/cornflow-client?label=cornflow-client&style=for-the-badge
  :alt: PyPI
  :target: https://pypi.python.org/pypi/cornflow-client

.. image:: https://img.shields.io/pypi/l/cornflow-client?color=blue&style=for-the-badge
  :alt: PyPI - License
  :target: https://github.com/baobabsoluciones/cornflow/blob/master/LICENSE

.. image:: https://img.shields.io/codecov/c/gh/baobabsoluciones/cornflow?flag=server-tests&label=cornflow&logo=codecov&logoColor=white&style=for-the-badge&token=H14UGPUQVL
   :alt: Codecov
   :target: https://app.codecov.io/gh/baobabsoluciones/cornflow

.. image:: https://img.shields.io/codecov/c/gh/baobabsoluciones/cornflow?flag=client-tests&label=client&logo=codecov&logoColor=white&style=for-the-badge&token=H14UGPUQVL
   :alt: Codecov
   :target: https://app.codecov.io/gh/baobabsoluciones/cornflow

.. image:: https://img.shields.io/codecov/c/gh/baobabsoluciones/cornflow?flag=dags-tests&label=dags&logo=codecov&logoColor=white&style=for-the-badge&token=H14UGPUQVL
   :alt: Codecov
   :target: https://app.codecov.io/gh/baobabsoluciones/cornflow


Cornflow is a collection of projects that allow for the rapid prototyping and deployment of optimization-based applications. Contrary to other existing deployment servers, Cornflow is centered around the applications and the problems, not in the techniques. It offers several other advantages such as being completely free (as in freedom) and very flexible.

Cornflow uses input and output schemas to define “optimization problems” and then accepts any (for now python) code that reads data in the input schema and returns a solution in the output schema. We use JSONSchema to define these schemas. By working like this, Cornflow becomes technique-agnostic without losing data-validation and re-usability (e.g., we can have more than one “solution method” for the same problem).

Being technique-agnostic implies we sometimes use CP models built with ortools, MIP models built with pyomo and some heuristics in pure python. But again, we could also have a localsolver model or any metaheuristic as long as it complies with the interface format for the particular optimization problem. In the :ref:`Examples of solution methods` section we describe some of the demo solution methods we have built and deployed.


Ways it can be used
---------------------

Cornflow main advantage is its flexibility and so it can be used and deployed in many ways. The easiest is to use the test server we already have deployed to test the current offer of solvers. For this, check the :ref:`User your solution method` section on how to test the server and then the :ref:`Examples of solution methods` section to see what solvers are available.

If you want to have your solution available in the server, feel free to propose a new solution method via a Pull Request. This is explained in section :ref:`How to deploy a new solution method (2.0)`.

Finally, if you want to deploy your own Cornflow-server privately and deploy your own private solution methods, you can check the several ways in which you can do that in :ref:`Deploy your own Cornflow-server`.

Components
-----------

Cornflow is composed of several components:

.. grid:: 1 1 2 2
  :padding: 2
  :gutter: 2

  .. grid-item-card:: Cornflow server

    The Cornflow server is the main component of the system. It is a Flask application that exposes a REST API to interact with the system. It is the component that receives the optimization problems and returns the solutions. It is also the component that manages the optimization problems and the solution methods.

  .. grid-item-card:: Cornflow client

    The Cornflow client is a python library that allows to interact with the Cornflow server. It is the component that allows to create and manage optimization problems and solution methods.

  .. grid-item-card:: Cornflow dags

    The Cornflow dags are a collection of airflow dags that allow to deploy the Cornflow server and the solution methods in a Kubernetes cluster. It is the component that allows to deploy the Cornflow server and the solution methods.

  .. grid-item-card:: airflow

    Airflow is a platform to programmatically author, schedule and monitor workflows. It is the component that allows to deploy the Cornflow server and the solution methods.