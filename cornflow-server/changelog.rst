version 1.3.0
--------------

- released: 2026-02-12
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - added support for Databricks as an execution backend.
    - added support for Microsoft Azure AD / Entra ID authentication.
    - changed health check endpoint to return ``backend_status`` instead of ``airflow_status``.
    - changed execution details to show ``run_id`` instead of ``dag_run_id``.
    - renamed ``DeployedDAG`` model to ``DeployedWorkflow``.

What's New for Users
====================

Major New Feature: Databricks Support
--------------------------------------

Cornflow now supports **Databricks** as an execution backend, giving you more flexibility in where your optimization models run.

**What this means for you:**

- You can now choose between Airflow or Databricks to execute your optimization models
- Both backends offer the same core functionality
- Existing Airflow users: nothing changes unless you want to switch
- Your data (instances) works with both backends

**How to use it:**

- Your system administrator configures which backend to use
- The Cornflow interface remains the same
- All your existing workflows continue to work

Changes You'll Notice
=====================

1. Health Check Response
------------------------

**What changed:**

- The health check endpoint now returns ``backend_status`` instead of ``airflow_status``

**Why it matters:**

- More accurate naming that reflects the multi-backend architecture
- You'll see which execution backend (Airflow or Databricks) is healthy

**Example:**

.. code-block:: json

   {
     "cornflow_status": "healthy",
     "backend_status": "healthy",  // ← Changed from "airflow_status"
     "cornflow_version": "1.3.0"
   }

**What you need to do:**

- If you're checking the health endpoint in your code, update ``airflow_status`` → ``backend_status``

2. Execution Information
------------------------

**What changed:**

- Execution details now show ``run_id`` instead of ``dag_run_id``

**Why it matters:**

- More generic naming that works with both Airflow and Databricks
- Same information, just a clearer name

**Example:**

.. code-block:: json

   {
     "id": "abc123",
     "run_id": "456789",  // ← Changed from "dag_run_id"
     "state": 1,
     "message": "Execution completed successfully"
   }

**What you need to do:**

- If you're reading execution data in your code, update ``dag_run_id`` → ``run_id``

3. Improved Azure AD Authentication
-----------------------------------

**What changed:**

- Better support for Microsoft Azure AD / Entra ID authentication

**Why it matters:**

- More reliable login for organizations using Azure AD
- Automatic detection of Azure endpoints
- Fewer authentication errors

**What you need to do:**

- Nothing! If you use Azure AD, authentication will just work better

4. Changed Model Class Names
----------------------------

If you're extending or integrating with the server, some model names have changed:

**Model Classes:**

+-----------------------------------------------+-----------------------------------------------+-------------------+
| Old Import                                    | New Import                                    | Status            |
+===============================================+===============================================+===================+
| ``from cornflow.models import DeployedDAG``   | ``from cornflow.models import DeployedWorkflow`` | ⚠️ Old name removed |
+-----------------------------------------------+-----------------------------------------------+-------------------+

**Example:**

.. code-block:: python

   # Old way (will cause ImportError)
   from cornflow.models import DeployedDAG
   dag = DeployedDAG.get_one_object("solve_model_dag")

   # New way (required)
   from cornflow.models import DeployedWorkflow
   workflow = DeployedWorkflow.get_one_object("solve_model_dag")

**What you need to do:**

- **Required:** Update imports from ``DeployedDAG`` to ``DeployedWorkflow``
- This is a breaking change - the old name no longer exists

Features Not Yet Available in Databricks
=========================================

If your system is configured to use Databricks, these features are not yet supported:

1. **Stop Execution**

   - You cannot manually stop a running execution
   - Trying to stop will return an error message
   - Available only with Airflow backend for now

2. **Example Data**

   - Viewing example instances and solutions through the API
   - Coming in a future update

What Still Works Exactly the Same
==================================

These features work identically regardless of your backend:

- Creating and managing instances
- Creating and running executions
- Viewing execution results
- Managing cases
- Comparing cases
- User authentication and permissions
- Data validation and checks
- All optimization solvers

For System Administrators
==========================

New Configuration Options
--------------------------

If you're setting up or maintaining a Cornflow installation:

**Backend Selection:**

.. code-block:: bash

   # Use Airflow (default - no change needed)
   CORNFLOW_BACKEND=1

   # Use Databricks (new option)
   CORNFLOW_BACKEND=2

**Database Migration:**

If you're upgrading from v1.2.x, run:

.. code-block:: bash

   flask db upgrade

This updates:

- Table names to use "workflow" terminology
- Execution tracking fields

**See:** ``Migration_guide.md`` for detailed administrator instructions

Need Help?
==========

Common Questions
-----------------

**Q: Do I need to do anything to upgrade?**

A: If you only use the web interface or API, very little:

   - Update any code that checks ``airflow_status`` → ``backend_status``
   - Update any code that uses ``dag_run_id`` → ``run_id``
   - Update imports from ``DeployedDAG`` to ``DeployedWorkflow`` if you're extending the server
   - Optionally update Python client method names (old ones still work)

**Q: Will my existing instances and executions still work?**

A: Yes! All your data is preserved and continues to work.

**Q: Can I switch between Airflow and Databricks?**

A: Your system administrator can switch backends by changing configuration. Your data remains accessible with either backend.

**Q: Do I need to change my optimization models?**

A: No! Models run the same way regardless of backend.

**Q: I'm seeing deprecation warnings in my Python code**

A: Update the method names as shown in the cornflow-client changelog. The old methods still work for now.

version 1.2.6
--------------

- released: 2025-10-31
- description: bump version code to stay up to date with cornflow-client.
- changelog:
    - updated cornflow-client to version 1.2.6

version 1.2.5
--------------

- released: 2025-10-09
- description:
- changelog:
    - updated cornflow-client to version 1.2.5
    - fixed OpenID authentication error with Microsoft.
    - added new fields to return on execution endpoint GET call.

version 1.2.4
--------------

- released: 2025-07-08
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - added new authenticated option for signup endpoint.
    - signup endpoint requires authentication of admin to create new users.
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
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - small fixes to documentation
    - refactored test so that they do not return anything.
    - default DAG update_dag_registry skips deleted apps.
    - fixed error when no data was passed on `Instance` creation.
    - fixed some filtering errors when using `offset`.
    - changed `datetime.utcnow()` to `datetime.now(timezone.utc)` to avoid future deprecation.
    - revamped OpenID authentication.
    - added `issuer` field for token authentication.
    - added `downgrade` command for migrations.
    - allowed commands to be run from inside docker container.
    - added `disable_detail` method on `BaseMetaResource`.


version 1.1.5
--------------

- released: 2025-01-14
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - when authenticating with Open Auth the service user can still log in with username and password.
    - allowed the application root to be changed.
    - bump minimal version from 3.8 to 3.9.
    - improved unit tests coverage.
    - added test descriptions.

version 1.1.4
--------------

- released: 2024-12-05
- description: same version as previous one.
- changelog:
    - new version due to pypi outage and problems with the version uploaded

version 1.1.3
--------------

- released: 2024-12-05
- description: small changes
- changelog:
    - changed the json schema validation on airflow so that solution, instance checks and solution checks are correctly reviewed.
    - added some small changes to make sure that future compatibility with new version of libraries is ready.
    - added a reconnect from airflow to cornflow to make sure that if the model fails we can get back as much as possible.

version 1.1.2
--------------

- released: 2024-10-31
- description: security fix
- changelog:
    - bump Werkzeug to version 3.0.6 due to CVE-2024-49766 and CVE-2024-49767.

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
- description: new version of cornflow with new features and bug fixes.
- changelog: 
  - custom token duration.
  - fixed errors on login.
  - added password rotation capabilities.
  - migrated some deprecated functions on dependencies.
  - updated documentation.

version 1.0.11
---------------

- released: 2024-05-10
- description: release to fix security vulnerabilities
- changelog:
    - Upgraded flask-cors version to 4.0.1
    - Upgraded Werkzeug version to 3.0.3
    - Upgraded Airflow to version 2.9.1
    - Fixed Werkzeug version on airflow image to 3.0.3

version 1.0.10
---------------

- released: 2024-04-17
- description: changed libraries versions due to discovered vulnerabilities
- changelog:
    - Upgraded cryptography version to 42.0.5
    - Upgraded gunicorn version to 22.0.0
    - Upgraded requests version to 2.31.0
    - Upgraded Werkzeug version to 2.3.8

version 1.0.9
--------------

- released: 2023-12-27
- description: added new authentication for BI endpoints where the token does not expire
- changelog:
    - Added new auth method.
    - Added new token generation that can be used only through the cli.
    - Added new token decodification that doe snot check for expiry date on token.

version 1.0.8
--------------

- released: 2023-10-20
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - This version of cornflow is only compatible with Python versions 3.8 or higher, with the desired version for deployment being Python version 3.10 (preferred version for baobab development as well).
    - This version of cornflow updates the version of airflow to 2.7.1.
    - Almost all library versions have been fixed to avoid dependency problems in future deployments.
    - In the ApplicationCore you can define a new class-level argument (like schemas) which is notify. This argument, when True, automatically adds a callback that will send us an email with the log attached in case the model fails when running in Airflow.
    - There is a new default DAG (run_deployed_models) that allows us to automatically launch all the models that we have deployed and for which we have defined a test instance in the ApplicationCore definition, so that once deployed we can do a quick test of the correct functioning of the model.
    - If we create an execution and in the configuration we have not included all the information, the default values defined in the configuration json schema are taken.
    - A command that used to convert models from an external app to jsonschemas is now disabled.


version 1.0.7
--------------

- released: 2023-10-03
- description: security version of cornflow to update vulnerability on dependency
- changelog:
    - updated version of gevent to 23.9.0.post1 due to security reasons.

version 1.0.5
--------------

- released: 2023-05-04
- description: first version of cornflow without cornflow core
- changelog:
    - removed cornflow core from dependencies.
    - moved all cornflow core code to cornflow.
    - added new error handling for InternalServerErrors.
    - updated version of flask to 2.3.2 due to security reasons.
    - updated version of other libraries due to upgrade on flask version.

version 1.0.4
---------------

- released: 2023-04-21
- description: added alarms models and endpoints that can be used, change the get of all executions, better error handling and new useful methods
- changelog:
    - when performing a get of all executions the running executions get their status updated
    - improve error handling
    - add alarms models and endpoints so they can be used on `external_apps`
    - added new useful methods



version 1.0.3
---------------


version 1.0.2
---------------

- released: 2023-03-17
- description: fixes error on startup on google cloud because the monkey patch from gevent was not getting applied properly on urllib3 ssl dependency.
- changelog:
    - applied monkey patch from gevent before app startup.
    - change on service command to not start up the gunicorn process inside the app context.
    - change on health endpoint so by default is unhealthy.
    - adjusted health endpoint unit and integration tests.
    - fixed version of cornflow-client to 1.0.11


version 1.0.1
---------------

- released: 2023-03-16
- description: fixed requirements versions in order to better handle the dockerfile construction on dockerhub.
- changelog:
    - fixed version of cornflow-core to 0.1.9
    - fixed version of cornflow-client to 1.0.10

version 1.0.0
--------------

- released: 2023-03-15
- description: initial release of cornflow package