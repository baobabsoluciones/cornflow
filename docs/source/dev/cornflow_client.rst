Cornflow-client
==========================

Core classes
------------------

ApplicationCore
*********************

.. automodule:: cornflow_client.core.application
   :members:
   :show-inheritance:
   :member-order: bysource

InstanceCore
*********************

.. automodule:: cornflow_client.core.instance
   :members:
   :show-inheritance:
   :member-order: bysource

SolutionCore
*********************

.. automodule:: cornflow_client.core.solution
   :members:
   :show-inheritance:
   :member-order: bysource

InstanceSolution
*********************

.. automodule:: cornflow_client.core.instance_solution
   :members:
   :show-inheritance:
   :member-order: bysource

ExperimentCore
*********************

.. automodule:: cornflow_client.core.experiment
   :members:
   :show-inheritance:
   :member-order: bysource


Cornflow client
------------------

.. automodule:: cornflow_client.cornflow_client
   :members:
   :show-inheritance:
   :member-order: bysource

Constants
------------------


Solving status
*********************

.. data:: cornflow_client.constants.STATUS_NOT_SOLVED
.. data:: cornflow_client.constants.STATUS_OPTIMAL
.. data:: cornflow_client.constants.STATUS_INFEASIBLE
.. data:: cornflow_client.constants.STATUS_UNBOUNDED
.. data:: cornflow_client.constants.STATUS_UNDEFINED
.. data:: cornflow_client.constants.STATUS_FEASIBLE
.. data:: cornflow_client.constants.STATUS_MEMORY_LIMIT
.. data:: cornflow_client.constants.STATUS_NODE_LIMIT
.. data:: cornflow_client.constants.STATUS_TIME_LIMIT
.. data:: cornflow_client.constants.STATUS_LICENSING_PROBLEM
.. data:: cornflow_client.constants.STATUS_QUEUED

============================================================  ==========
Constant                                                       Value
============================================================  ==========
:data:`cornflow_client.constants.STATUS_NOT_SOLVED`              0
:data:`cornflow_client.constants.STATUS_OPTIMAL`                 1
:data:`cornflow_client.constants.STATUS_INFEASIBLE`              -1
:data:`cornflow_client.constants.STATUS_UNBOUNDED`               -2
:data:`cornflow_client.constants.STATUS_UNDEFINED`               -3
:data:`cornflow_client.constants.STATUS_FEASIBLE`                2
:data:`cornflow_client.constants.STATUS_MEMORY_LIMIT`            3
:data:`cornflow_client.constants.STATUS_NODE_LIMIT`              4
:data:`cornflow_client.constants.STATUS_TIME_LIMIT`              5
:data:`cornflow_client.constants.STATUS_LICENSING_PROBLEM`       -5
:data:`cornflow_client.constants.STATUS_QUEUED`                  -7
============================================================  ==========


Solution status
*********************

.. data:: cornflow_client.constants.SOLUTION_STATUS_INFEASIBLE
.. data:: cornflow_client.constants.SOLUTION_STATUS_FEASIBLE


============================================================  ==========
Constant                                                       Value
============================================================  ==========
:data:`cornflow_client.constants.SOLUTION_STATUS_INFEASIBLE`       0
:data:`cornflow_client.constants.SOLUTION_STATUS_FEASIBLE`          2
============================================================  ==========


.. automodule:: cornflow_client.constants
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:
   :member-order: bysource

Schemas
------------------

Schema utility functions
***************************


.. automodule:: cornflow_client.schema.tools
   :members:
   :show-inheritance:
   :member-order: bysource

Schema manager
*********************

.. automodule:: cornflow_client.schema.manager
   :members:
   :show-inheritance:
   :member-order: bysource

Dictionary schema
*********************

.. automodule:: cornflow_client.schema.dictSchema
   :members:
   :show-inheritance:
   :member-order: bysource
