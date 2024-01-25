Test your solution method
=============================================

Basics of testing
------------------------------

The `cornflow-dags <https://github.com/baobabsoluciones/cornflow/tree/master/cornflow-dags>`_ project includes some unit tests that can be run to be sure the projects are “ready to be merged”. These unit tests use as input data the output of the function ``test_cases()`` defined in cornflow-dags/DAG/my_project/__init__.py. The tests themselves load the data, validate it with the schema, solve the problem, get a solution and validate it.

In order for your dag to be tested along with the others, you should add it to the unit tests to be run. The file to modify is ``cornflow-dags/tests/test_dags.py``. In this file, you must add a class corresponding to your project. It should look something like:

.. code-block:: python

    class MyProject(BaseDAGTests.SolvingTests):
       def setUp(self):
           super().setUp()
           from DAG.MyProject import MyApp
           self.app = MyApp()                   # Will test the default solver


       def test_solve_algo_1(self):
           return self.test_try_solving_testcase(dict(solver="algorithm1"))
                                                     # Will test another solver


Test locally
---------------

Once the tests are defined, it’s possible to run them in the local machine. To do this, you need to do the following:

.. code-block:: bash

    python3 -m unittest tests/test_dags.py


This should run all tests for all applications. If you only want to run tests for your application, you can do:

.. code-block:: bash

    python3 -m unittest tests.test_dags.MyProject

Test in github
-----------------

When the source code for your application is uploaded to the git repository, github will perform the same unit tests for each of the dags to check whether the code produces errors. It will also run some additional tests.
