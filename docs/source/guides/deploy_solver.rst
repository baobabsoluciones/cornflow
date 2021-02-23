How to deploy a new solver
==========================


There are several things that are needed when submitting a new solver.

1. a `solve` function.
2. a `name` string.
3. an `instance` dictionary.
4. an `solution` dictionary.
5. (optional) a `test_cases` function that returns a list of dictionaries.

In its most minimalistic form: an app constitutes one dag file that contains all of this.
In the following lines we will explain each of these concepts.

The solver
------------

The solver comes in the form of a python function that takes exactly two arguments: `data` and `config`. The first one is a dictionary with the input data (Instance) to solve the problem. The second one is also a dictionary with the execution configuration.

This function needs to be named `solve` and returns three things: a dictionary with the output data (Solution), a string that stores the whole log, and a dictionary with the log information processed.


Name
-----

Just put a name and use it inside the DAG generation. The name *needs* to be defined as a separate variable!

The input schema and output schema
-----------------------------------------

Both schemas are built and deployed similarly so we present how the input schema is done.

The input schema is a json schema file (https://json-schema.org/) that includes all the characteristics of the input data for each dag. This file can be built with many tools (a regular text editor could be enough). We will detail how to do this later.

The input schema is stored in the Variables storage of Airflow. In order to upload it: you need to have an `instance` variable available in your dag file.


Once uploaded, these schemas will be accessible to cornflow and will be used to validate input data and solutions for this dag.

Test cases
------------

This function is used in the unittests to be sure the solver works as intended.
