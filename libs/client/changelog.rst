version 1.3.0
--------------

- released: 2026-02-12
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - added new method names that are clearer and more generic.
    - added new exception classes for better error handling.

Cornflow Client Updates (Python Library)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. New Method Names Available
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use the Cornflow Python client (``cornflow-client``), we've added new method names that are clearer and more generic:

+---------------------------+------------------------------+----------------------------------+
| What You Used Before      | What You Can Use Now         | Status                           |
+===========================+==============================+==================================+
| ``get_dag_info()``        | ``get_workflow_info()``      | ✅ Both work (old shows warning) |
+---------------------------+------------------------------+----------------------------------+
| ``run_dag()``             | ``run_workflow()``           | ✅ Both work (old shows warning) |
+---------------------------+------------------------------+----------------------------------+
| ``get_dag_run_status()``  | ``get_run_status()``         | ✅ Both work (old shows warning) |
+---------------------------+------------------------------+----------------------------------+

**Example of the change:**

.. code-block:: python

   # Old way (still works but shows warning)
   client.run_dag(execution_id="123", dag_name="solve_model_dag")

   # New way (recommended)
   client.run_workflow(execution_id="123", workflow_name="solve_model_dag")

**What you need to do:**

- **Optional:** Update to the new method names when convenient
- **Required eventually:** The old names will be removed in a future major version (2.0.0)
- For now, both work - you'll just see deprecation warnings with the old names

2. Changed Exception Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Exception Classes:**

+--------------------------------------------------------+--------------------------------------------------------+-------------------+
| Old Import                                             | New Import                                             | Status            |
+========================================================+========================================================+===================+
| ``from cornflow_client.constants import AirflowError`` | Still works (no change needed)                         | ✅ Still available |
+--------------------------------------------------------+--------------------------------------------------------+-------------------+
| N/A                                                    | ``from cornflow_client.constants import DatabricksError`` | ✨ New class      |
+--------------------------------------------------------+--------------------------------------------------------+-------------------+
| N/A                                                    | ``from cornflow_client.constants import OrchError``    | ✨ New base class |
+--------------------------------------------------------+--------------------------------------------------------+-------------------+

**Example:**

.. code-block:: python

   # If you were catching AirflowError
   from cornflow_client.constants import AirflowError

   try:
       client.run_workflow(...)
   except AirflowError as e:
       print(f"Execution failed: {e}")

   # New: You can also catch the base class for both backends
   from cornflow_client.constants import OrchError

   try:
       client.run_workflow(...)
   except OrchError as e:  # Catches both AirflowError and DatabricksError
       print(f"Execution failed: {e}")

**What you need to do:**

- **Optional:** Consider catching ``OrchError`` instead of ``AirflowError`` if you want to handle both backends
- ``AirflowError`` still works and is not deprecated
- ``DatabricksError`` is available if you need backend-specific error handling

version 1.2.6
--------------

- released: 2025-10-31
- description: New check control
- changelog:
    - When a check has a coding error, it is now displayed in the instance/solution checks with the message: "The execution of the check has failed. Please contact support."

version 1.2.5
--------------

- released: 2025-10-09
- description: bump version code to stay up to date with cornflow-server.
- changelog:
    - updated cornflow-client to version 1.2.5


version 1.2.4
--------------

- released: 2025-07-08
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - fixed error on parameter parsing for gurobi.
    - changed requests version to 2.32.4 due to security issues.

version 1.2.3
--------------

- released: 2025-06-10
- description: Bug fixes for permissions management and view handling
- changelog:
    - Fixed view modification functionality that was not properly updating URL rules and endpoint configurations.
    - Resolved permission deletion issues where orphaned permissions were not being correctly removed from the database.
    - Enhanced custom roles functionality to work properly with external applications. For detailed configuration information, please refer to the Cornflow documentation.


version 1.2.2
--------------

- released: 2025-05-21
- description: Small changes on execution endpoint and sonarqube related changes
- changelog:
    - Added fields of username and updated at to GET /execution/ response
    - Added flexibility to /execution/ get-detail schema (for config read)
    - Added new action (sonarqube related)


version 1.2.1
--------------

- released: 2025-04-03
- description: security update
- changelog:
    - updated gunicorn version to 23.0.0
    - updated cryptography version to 44.0.1


version 1.2.0
--------------

- released: 2025-03-12
- description: new features
- changelog:
    - fixed `get_solver_config` method.
    - added method to run automatically `Instance` and `Experiment` checks.
    - changed the way the token is sent on cornflow-client library.

version 1.1.5
--------------

- released: 2025-01-14 
- description: added support for python 3.12
- changelog:
    - added support for python 3.12.
    - dropped support for python 3.8.
    - updated requirements versions.

version 1.1.4
------------

- released: 2024-12-05
- description: same version as previous one.
- changelog:
    - new version due to pypi outage and problems with the version uploaded

version 1.1.3
------------

- released: 2024-12-05
- description: changes to json schemas validation on airflow.
- changelog:
    - changed the json schema validation on airflow so that solution, instance checks and solution checks are correctly reviewed.
    - added some small changes to make sure that future compatibility with new version of libraries is ready.
    - added a reconnect from airflow to cornflow to make sure that if the model fails we can get back as much as possible.


version 1.1.1
--------------

- released: 2024-09-18
- description: small security fixes
- changelog:
    - bump PuLP to version 2.9.0
    - bump requests to version 2.32.3
    - modified branch structure on repository.
    - minor changes to documentation

version 1.1.0
--------------

- released: 2024-05-22
- description: Changed the way test cases are stored
- changelog:
  - changed the way test cases are stored.
  - changed what the log stores when solverolving the application.


version 1.0.16
---------------

- released: 2023-10-20
- description: Small fixes to the cornflow-client
- changelog:

version 1.0.15
---------------

- released: 2023-10-04
- description: dropped Python 3.7 support
- changelog:
    - dropped python 3.7 support as will the rest of components.


version 1.0.14
---------------

- released: 2023-10-03
- description: added pandas dependency due to ortools missing pandas as their own dependency
- changelog:
    - added pandas (>=1.5.2) dependency due to ortools missing pandas as their own dependency

version 1.0.13
---------------

- released: 2023-05-04
- description: bugfix on error handling in dag solving workflow
- changelog:
    - bugfix on error handling in dag solving workflow
    - calls to cornflow now use the raw client.

version 1.0.12
---------------

- released: 2023-04-21
- description: added solver paramaeter translation function
- changelog:
    - added solver paramaeter translation function

version 1.0.11
----------------

- released: 2023-03-17
- description: change the way airflow api behaves doing the is_alive check.
- changelog:
    - change the way airflow api behaves doing the is_alive check.
