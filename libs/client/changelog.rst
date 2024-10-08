version 1.1.1
--------------

- released: 2024-08-29
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
