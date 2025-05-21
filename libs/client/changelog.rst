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
