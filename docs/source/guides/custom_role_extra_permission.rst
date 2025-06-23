Custom role and extra permissions configuration
=================================================

Overview
--------

Cornflow provides two powerful mechanisms to configure custom permissions in external applications: 
``CUSTOM_ROLES_ACTIONS`` for defining default actions for custom roles, and ``EXTRA_PERMISSION_ASSIGNATION`` 
for assigning specific additional permissions to any role on particular endpoints.

What it Provides
-----------------

Cornflow's permission system provides flexible permission management for external applications:

- **Custom Role Configuration**: Define specific default actions for custom roles according to business needs
- **Granular Permission Assignment**: Assign additional permissions to any role (custom or standard) on specific endpoints
- **Fine-grained Control**: Achieve precise permission control at the endpoint level
- **Flexible Extension**: Extend standard roles with additional permissions for specific use cases

Configuration
-------------

1. Define Constants in the External App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In your external app's ``shared/const.py`` file, define both ``CUSTOM_ROLES_ACTIONS`` and ``EXTRA_PERMISSION_ASSIGNATION`` constants:

.. code-block:: python

    from cornflow.shared.const import GET_ACTION, POST_ACTION, PUT_ACTION, PATCH_ACTION
    from cornflow.shared.const import VIEWER_ROLE, PLANNER_ROLE

    # Dictionary mapping each custom role to its allowed default actions
    CUSTOM_ROLES_ACTIONS = {
        # Production role - can read, create and update
        888: [GET_ACTION, POST_ACTION, PUT_ACTION],
        # Quality role - can read and partially modify           
        777: [GET_ACTION, PATCH_ACTION],
        # Read-only role                      
        999: [GET_ACTION],
        # Custom admin role
        1001: [GET_ACTION, POST_ACTION, PUT_ACTION, PATCH_ACTION],  
    }

    # List of specific additional permissions (role_id, action_id, endpoint_name)
    EXTRA_PERMISSION_ASSIGNATION = [
        # Give production role patch permission on specific endpoint
        (888, PATCH_ACTION, "production_planning"),
        # Give standard viewer role post permission on reports endpoint
        (VIEWER_ROLE, POST_ACTION, "reports"),
        # Give quality role put permission on quality control endpoint
        (777, PUT_ACTION, "quality_control"),
        # Give standard planner role patch permission on scheduling endpoint
        (PLANNER_ROLE, PATCH_ACTION, "scheduling_optimizer"),
    ]

2. Use Roles in Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~

In your endpoints, define which roles have access using ``ROLES_WITH_ACCESS``:

.. code-block:: python

    class ProductionPlanningResource(BaseInstanceResource):
        # Custom role 888 + standard role
        ROLES_WITH_ACCESS = [888, PLANNER_ROLE]  
        DESCRIPTION = "Production planning endpoint"
        
        # ... rest of implementation

    class QualityControlResource(BaseInstanceResource):
        # Custom role 777 + standard role
        ROLES_WITH_ACCESS = [777, VIEWER_ROLE]   
        DESCRIPTION = "Quality control endpoint"
        
        # ... rest of implementation

3. Complete External App Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

    external_app/
    ├── shared/
    │   └── const.py              # Contains CUSTOM_ROLES_ACTIONS and EXTRA_PERMISSION_ASSIGNATION
    ├── endpoints/
    │   ├── __init__.py
    │   └── resources.py          # Defines endpoints with ROLES_WITH_ACCESS
    └── __init__.py

Complete Example
----------------

external_app/shared/const.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cornflow.shared.const import GET_ACTION, POST_ACTION, PUT_ACTION, PATCH_ACTION
    from cornflow.shared.const import VIEWER_ROLE, PLANNER_ROLE

    # Default actions for custom roles
    CUSTOM_ROLES_ACTIONS = {
        # Production role
        888: [GET_ACTION, POST_ACTION, PUT_ACTION],    
        # Quality role
        777: [GET_ACTION, PATCH_ACTION],               
        # Query role
        999: [GET_ACTION],                             
    }

    # Additional specific permissions per endpoint
    EXTRA_PERMISSION_ASSIGNATION = [
        # Give production role patch permission on production planning
        (888, PATCH_ACTION, "production_planning"),
        # Give standard viewer role post permission on reports
        (VIEWER_ROLE, POST_ACTION, "reports"),
        # Give quality role additional permissions
        (777, PUT_ACTION, "quality_control"),
        (777, PATCH_ACTION, "quality_control"),
        # Extend planner role with patch permission on specific endpoint
        (PLANNER_ROLE, PATCH_ACTION, "scheduling_optimizer"),
    ]

external_app/endpoints/resources.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cornflow.endpoints import BaseInstanceResource
    from cornflow.shared.const import PLANNER_ROLE, VIEWER_ROLE

    class ProductionPlanningResource(BaseInstanceResource):
        ROLES_WITH_ACCESS = [888, PLANNER_ROLE]
        DESCRIPTION = "Production planning endpoint"

    class QualityControlResource(BaseInstanceResource):
        ROLES_WITH_ACCESS = [777, VIEWER_ROLE] 
        DESCRIPTION = "Quality control endpoint"

    class ReportsResource(BaseInstanceResource):
        ROLES_WITH_ACCESS = [999, 888, 777, VIEWER_ROLE]
        DESCRIPTION = "Reports endpoint - accessible by multiple roles"

    # Resource list for export
    resources = [
        {
            "endpoint": "production_planning",
            "urls": "/production-planning/",
            "resource": ProductionPlanningResource,
        },
        {
            "endpoint": "quality_control", 
            "urls": "/quality-control/",
            "resource": QualityControlResource,
        },
        {
            "endpoint": "reports",
            "urls": "/reports/",
            "resource": ReportsResource,
        },
    ]

How Both Systems Work Together
------------------------------

Understanding the Permission Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The permission system works in two phases:

1. **Base Permissions from CUSTOM_ROLES_ACTIONS**: Each custom role receives its default actions on all endpoints where it appears in ``ROLES_WITH_ACCESS``
2. **Additional Permissions from EXTRA_PERMISSION_ASSIGNATION**: Specific additional permissions are granted to any role (custom or standard) on particular endpoints

Example Permission Flow
~~~~~~~~~~~~~~~~~~~~~~~

Given this configuration:

.. code-block:: python

    CUSTOM_ROLES_ACTIONS = {
        888: [GET_ACTION, POST_ACTION],  # Default actions for role 888
    }

    EXTRA_PERMISSION_ASSIGNATION = [
        (888, PATCH_ACTION, "production_planning"),  
        (VIEWER_ROLE, POST_ACTION, "reports"),        # Extend standard role
    ]

And these endpoints:

.. code-block:: python

    class ProductionPlanningResource(BaseInstanceResource):
        ROLES_WITH_ACCESS = [888, PLANNER_ROLE]

    class ReportsResource(BaseInstanceResource):
        ROLES_WITH_ACCESS = [888, VIEWER_ROLE]

The resulting permissions will be:

- **Role 888 on production_planning**: GET, POST (from CUSTOM_ROLES_ACTIONS) + PATCH (from EXTRA_PERMISSION_ASSIGNATION)
- **Role 888 on reports**: GET, POST (from CUSTOM_ROLES_ACTIONS)
- **PLANNER_ROLE on production_planning**: Standard planner permissions (from BASE_PERMISSION_ASSIGNATION)
- **VIEWER_ROLE on reports**: Standard viewer permissions + POST (from EXTRA_PERMISSION_ASSIGNATION)

Validations and Errors
-----------------------

Error for Undefined Role
~~~~~~~~~~~~~~~~~~~~~~~~~

If a custom role is used in ``ROLES_WITH_ACCESS`` but not defined in ``CUSTOM_ROLES_ACTIONS``, a ``ValueError`` will be raised:

.. code-block::

    ValueError: The following custom roles are used in code but not defined in CUSTOM_ROLES_ACTIONS: {888}. 
    Please define their allowed actions in the CUSTOM_ROLES_ACTIONS dictionary in shared/const.py.

Error Example
~~~~~~~~~~~~~

.. code-block:: python

    # ❌ INCORRECT - Role 888 used but not defined
    CUSTOM_ROLES_ACTIONS = {
        # Only role 777 is defined
        777: [GET_ACTION, PATCH_ACTION],  
    }

    # In endpoints role 888 is used -> ERROR
    class ProductionResource(BaseInstanceResource):
        # 888 is not defined in CUSTOM_ROLES_ACTIONS
        ROLES_WITH_ACCESS = [888, PLANNER_ROLE]  

Solution
~~~~~~~~

.. code-block:: python

    # ✅ CORRECT - All roles are defined
    CUSTOM_ROLES_ACTIONS = {
        777: [GET_ACTION, PATCH_ACTION],
        # Now 888 is defined
        888: [GET_ACTION, POST_ACTION, PUT_ACTION],  
    }

Backward Compatibility
----------------------

- If an external app doesn't define ``CUSTOM_ROLES_ACTIONS`` or ``EXTRA_PERMISSION_ASSIGNATION``, functionality continues to work normally
- Standard roles (``VIEWER_ROLE``, ``PLANNER_ROLE``, ``ADMIN_ROLE``, ``SERVICE_ROLE``) are not affected
- ``CUSTOM_ROLES_ACTIONS`` is only required if custom roles are used
- ``EXTRA_PERMISSION_ASSIGNATION`` is optional and can be used independently of custom roles

Available Actions
-----------------

The available actions you can use in ``CUSTOM_ROLES_ACTIONS`` are:

.. code-block:: python

    # Read (GET)
    GET_ACTION = 1      
    # Partial update (PATCH)
    PATCH_ACTION = 2    
    # Create (POST)
    POST_ACTION = 3     
    # Full update (PUT)
    PUT_ACTION = 4   