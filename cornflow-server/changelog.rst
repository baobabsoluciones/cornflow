version 1.4.0rc1
----------------
- released: pending
- description: Security levels and secret key handling
- changelog:
    - Security levels
        New variable ``CORNFLOW_SECURITY_LEVEL`` (1, 2 or 3; 1 by default) that sets the default value
        of every security setting. Level 1 behaves as version 1.3.9, so upgrading needs no change in
        deployments or clients (except the 401 answer to invalid tokens and the removal of the
        ``cornflow users create token`` command, both described below); level 2 adds the password
        policy, one-time passwords, account lockout after 5 failed logins, a mandatory secret key and
        8-hour sessions; level 3 adds mandatory two-factor authentication, renewable sessions, password
        rotation, user sign-up restricted to platform administrators, BI tokens that expire after 90
        days, closed CORS, Swagger off and HSTS on, whatever ``FLASK_ENV`` is. An invalid level stops
        cornflow from starting. The effective level and the variables that change its defaults are
        logged at startup; the level is not exposed through the API.

    - Settings by level
        Every security setting keeps its own variable, which overrides the level default within the
        limits of the level. A value outside the limits is replaced by the limit, with a warning in the
        log; a 0 that turns off a control the level requires (``LOGIN_MAX_ATTEMPTS`` at levels 2 and 3,
        ``BI_TOKEN_DURATION_DAYS`` at level 3) stops cornflow from starting. ``BI_TOKEN_DURATION_DAYS=0``
        issues BI tokens without expiration date. ``CORS_ORIGINS``, ``CORNFLOW_DOCS_ENABLED`` and
        ``HSTS_ENABLED`` no longer depend on ``FLASK_ENV``.

    - Two-factor enrollment
        New variable ``MFA_ENABLED`` (0 at levels 1 and 2, 1 at level 3). With ``MFA_ENABLED=0``,
        ``/mfa/setup/`` and ``/mfa/verify/`` answer 501 and users who already enrolled keep using their
        second factor. ``MFA_REQUIRED``, ``API_KEY_STEPUP_TOTP`` and ``PLATFORM_ROLE_STEPUP_TOTP`` set to
        1 need ``MFA_ENABLED=1``, or cornflow does not start.

    - Secret key
        The secret key comes from ``FERNET_KEY`` and, if it is not set, from ``SECRET_KEY``. An empty
        variable counts as unset, and a warning is logged when both are set with different values. The
        key is resolved in the configuration, so the server and the CLI sign with the same one. Levels 2
        and 3 do not start without a key of at least 32 bytes; at level 1 without a key, cornflow uses a
        random key generated once per start and shared by all the gunicorn workers, with a warning.
        ``cornflow service init`` no longer writes ``SECRET_KEY`` (it used to fill it with ``FERNET_KEY``
        or with a new random key on every start) and no longer sets ``SIGNUP_ACTIVATED``.

    - Invalid tokens
        At every level, an expired token, a token with a wrong signature or format (also from OpenID
        Connect), a revoked session or API key, the token of a user that no longer exists and an expired
        or invalid BI token answer 401 with the header ``WWW-Authenticate: Bearer error="invalid_token"``.
        Several of these cases answered 400 in version 1.3.9. Requests without a token, or with a header
        that does not follow ``Bearer <token>``, still answer 400.

    - Rate limits
        The per-IP limit of login, token refresh and logout only counts failed responses, so successful
        logins (also those of the Airflow tasks) no longer use it up. Password recovery and reset still
        count every request.

    - Default passwords
        ``cornflow service init`` and the Airflow initialization script go back to the default passwords
        of version 1.3.9 for the admin and service users. They do not comply with the password policy
        of levels 2 and 3, where ``CORNFLOW_ADMIN_PWD`` and ``CORNFLOW_SERVICE_PWD`` must be set.

    - Docker and Helm
        The docker-compose files set a development-only ``FERNET_KEY`` and ``SECRET_BI_KEY`` and include
        ``CORNFLOW_SECURITY_LEVEL`` commented out. The Helm chart generates ``FERNET_KEY`` and
        ``SECRET_BI_KEY`` in a Secret that is kept across upgrades (or uses an existing one with
        ``cornflow.keys.existingSecret``), no longer sets ``SECRET_KEY``, adds
        ``CORNFLOW_SECURITY_LEVEL`` and requires Helm 3.5 or later.

    - BI token command
        Breaking change: the ``cornflow users create token`` command has been removed. Use
        ``cornflow users bi_token -u <username>`` or, better, a read-only personal API key
        (``cornflow users api_key -u <username> --read-only``).

    - Two-factor reset
        Resetting the two-factor authentication of a user (``DELETE /user/<id>/mfa/``) also revokes
        the personal API key superseded by the last rotation that is still in its grace window, as
        the account lock does.

    - Interactive API docs
        With ``CORNFLOW_DOCS_ENABLED=1`` (the default at levels 1 and 2) the routes of the Swagger UI
        (the page, its static files and the OpenAPI schema) get a Content-Security-Policy of their
        own that lets the interface load and work in the browser, with no external resources. The
        rest of the API keeps the strict policy, or ``CONTENT_SECURITY_POLICY`` if it is set.

version 1.3.5
--------------
- released: 2026-06-03
- description: KPIs in data checks, execution output files and new role
- changelog:
    - KPIs in data checks
        Executions and cases can now generate/re-generate and validate KPIs as part of the data-check flow. Solvers
        can define a KPI schema for their solutions, and the result is validated against it. The rostering
        example includes an implementation. New KPI-aware data-check endpoints are added alongside the
        existing data-check endpoints, which remain available.

    - Execution output files
        Adds the ability to generate output files for executions. These files are produced as part of the
        workflow run in Airflow, which follows the sequence:

        instance checks → solve → solution checks → KPIs → output files

        Each step gates the next:
        - **Instance checks** run first. If they report critical errors, the solver is not run and **no
          output files are generated**.
        - The **solver** runs. If no solution is found, output files are still produced based on the
          available data (instance checks).
        - **Solution checks** run on the solution. **KPIs are only generated when the solution checks
          report no errors**; if the solution has errors, KPIs are skipped.
        - **Output files** are then generated from the instance checks, solution, solution checks, and
          KPIs. Whether files are produced depends on the solver's `generate_output_files`
          implementation — if it returns nothing, files are reported as not generated.

        Each execution tracks the status of its files (not generated, ready/OK, out of date, deleted, or
        error), each with an associated message. If file generation fails at any point, the status is set
        to error. New endpoints let clients fetch these files and trigger regeneration, and a scheduled
        cleanup job removes stale execution files from the backend. Database migrations are included for
        the new fields.

    - Roles
        Adds a new "dummy" role with a limited set of permissions (read/update user detail, read user
        roles).

    -  Other changes
        Expanded test coverage for the new features.

version 1.3.4
--------------

- released: 2026-04-20
- description: Each user can get their role
- changelog:
    - Each user can get their role

version 1.3.3
--------------

- released: 2026-03-18
- description: Security release
- changelog:
    - updated some requirements

version 1.3.1
--------------

- released: 2026-03-05
- description: Security release
- changelog:
    - fixed versions in requirements, no more ranges
    - updated some requirements

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
~~~~~~~~~~~~~~~~~~~~

Major New Feature: Databricks Support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
~~~~~~~~~~~~~~~~~~~~~

1. Health Check Response
^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**What changed:**

- Better support for Microsoft Azure AD / Entra ID authentication

**Why it matters:**

- More reliable login for organizations using Azure AD
- Automatic detection of Azure endpoints
- Fewer authentication errors

**What you need to do:**

- Nothing! If you use Azure AD, authentication will just work better

4. Changed Model Class Names
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your system is configured to use Databricks, these features are not yet supported:

1. **Stop Execution**

   - You cannot manually stop a running execution
   - Trying to stop will return an error message
   - Available only with Airflow backend for now

2. **Example Data**

   - Viewing example instances and solutions through the API
   - Coming in a future update

What Still Works Exactly the Same
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~

New Configuration Options
^^^^^^^^^^^^^^^^^^^^^^^^^^

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
~~~~~~~~~~

Common Questions
^^^^^^^^^^^^^^^^^

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