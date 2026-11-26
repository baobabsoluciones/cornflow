version 1.4.0
--------------
- released: pending
- description: Security hardening with three security levels, plugins and a fixed secret key
- changelog:
    - Upgrading from version 1.3.9
        This version needs three database migrations (``b7a1c9d807e5``, ``c3f2a1b4e5d6`` and
        ``d4e8b2c6f109``), which ``cornflow service init`` applies at startup: new columns in the
        ``users`` table and the new tables ``user_password_history``, ``mfa_backup_codes`` and
        ``session_tokens``. At the default security level (1) cornflow behaves as version 1.3.9 for
        sessions, passwords, CORS, Swagger, HSTS, BI tokens and user sign-up. The changes that can
        affect a deployment or a client of version 1.3.9 start with "Breaking change" in the topics
        below. Set ``FERNET_KEY`` to a fixed value (see "Secret key"), and read "Raising the security
        level" in the access control documentation before moving to level 2 or 3.

    - Security levels
        New variable ``CORNFLOW_SECURITY_LEVEL`` (1, 2 or 3; 1 by default) that sets the default value
        of every security setting. The levels add up: level 1 behaves as version 1.3.9 for sessions,
        passwords, CORS, Swagger, HSTS, BI tokens and user sign-up; level 2 adds the password policy,
        one-time passwords, account lockout after 5 failed logins, user sign-up restricted to platform
        administrators (``SIGNUP_ACTIVATED=3``), a mandatory secret key of at least 32 bytes and
        8-hour sessions; level 3 adds mandatory two-factor authentication, renewable sessions, password
        rotation, BI tokens that expire after 90 days, closed CORS, Swagger off and HSTS on, whatever
        ``FLASK_ENV`` is. From level 2 client administrators no longer manage roles, permissions,
        actions and API views, and at level 3 they can no longer unlock accounts. An invalid level
        stops cornflow from starting. The effective level and the variables that change its defaults
        are logged at startup; the level is not exposed through the API.

    - Settings by level
        Every security setting keeps its own variable, which overrides the level default within the
        limits of the level. A value outside the limits is replaced by the limit, with a warning in the
        log; a 0 that turns off a control the level requires (``LOGIN_MAX_ATTEMPTS`` at levels 2 and 3,
        ``BI_TOKEN_DURATION_DAYS`` at level 3) stops cornflow from starting. ``CORS_ORIGINS``,
        ``CORNFLOW_DOCS_ENABLED`` and ``HSTS_ENABLED`` no longer depend on ``FLASK_ENV``, and
        ``cornflow service init`` no longer sets ``SIGNUP_ACTIVATED``, so the level default applies.
        ``cornflow service init`` exits with the reason, before running the migrations or creating any
        user, when the security configuration is not valid.

    - Password policy, rotation and one-time passwords
        At levels 2 and 3 a password must have at least 12 characters, uppercase and lowercase letters,
        a number and a special character, no spaces, no sequence of 6 or more digits and no personal
        data, and reach a zxcvbn strength score of 3; the last 10 passwords can not be reused, users
        send ``current_password`` to change their own password and the new one can not be too similar
        to it (``PWD_MIN_LENGTH``, ``PWD_MIN_ZXCVBN_SCORE``, ``PWD_HISTORY_SIZE`` and
        ``PWD_MAX_SIMILARITY``). Level 1 keeps the rules of version 1.3.9. From level 2 the passwords
        set by an administrator (also at sign-up), the temporary password of the recovery and the users
        flagged by the migration or created with the new ``--force-password-change`` option of
        ``cornflow users create`` must be changed at the next login: until then the other endpoints
        answer 403 with ``error_code: password_rotation``. At level 3 (``PWD_ROTATION_ENFORCE=1``) a
        password older than ``PWD_ROTATION_TIME`` days (120) can only be changed; at levels 1 and 2 it
        is only reported with ``change_password`` in the login response, as in version 1.3.9.

    - Two-factor authentication
        Internal users can add a second factor based on TOTP (RFC 6238), compatible with any
        authenticator app: ``POST /mfa/setup/`` returns the secret and the provisioning URI, and
        ``POST /mfa/verify/`` activates it and returns one-time backup codes. The login then answers
        ``mfa_required`` until it gets ``totp_code`` (a TOTP code or an unused backup code), and a code
        can not be used twice. The secrets are stored encrypted with a key derived from the secret key.
        ``DELETE /user/<id>/mfa/`` (the user or an administrator) removes the second factor and revokes
        the sessions and the personal API keys of the user, including the key superseded by the last
        rotation that is still in its grace window. New variable ``MFA_ENABLED`` (0 at levels 1 and 2,
        1 at level 3): with ``MFA_ENABLED=0``, ``/mfa/setup/`` and ``/mfa/verify/`` answer 501 and users
        who already enrolled keep using their second factor. With ``MFA_REQUIRED=1`` (level 3) every
        internal user except service users must enroll at the next login, which returns
        ``mfa_setup_required`` and a short-lived enrollment token; ``/signup/`` returns that token only
        on a self sign-up, not to the administrator who creates the account. ``MFA_REQUIRED``,
        ``API_KEY_STEPUP_TOTP`` and ``PLATFORM_ROLE_STEPUP_TOTP`` set to 1 need ``MFA_ENABLED=1``, or
        cornflow does not start. Service users and LDAP and OpenID users are exempt.

    - Account lockout
        After ``LOGIN_MAX_ATTEMPTS`` consecutive failed logins (wrong password or wrong second-factor
        code, also a wrong ``current_password`` in a password change) the account is locked until someone unlocks it: 0 at level 1 (no lockout, as in version
        1.3.9) and 5 at levels 2 and 3, where it must be between 1 and 10. The lock revokes the sessions
        and the personal API keys of the user. A locked account gets 403 with
        ``error_code: account_locked`` only when the password is correct. Platform administrators unlock
        any account with ``PUT /user/<id>/unlock/`` and, at levels 1 and 2, client administrators unlock
        the users without a platform role; ``cornflow users unlock -u <username>`` works at every level.
        Service users are exempt.

    - Sessions
        Tokens carry a version checked on every request, so a password change (also your own, which
        requires logging in again), an account lock or a two-factor reset closes all the sessions of
        the user. With ``REFRESH_TOKEN_ENABLED=1`` (the default at level 3) the login returns a short
        access token (``ACCESS_TOKEN_DURATION_MINUTES``, 15) and a refresh token that only works on
        ``POST /token/refresh/``, which rotates it. A session is closed after
        ``REFRESH_TOKEN_INACTIVITY_MINUTES`` (30) without a refresh and after
        ``REFRESH_TOKEN_ABSOLUTE_HOURS`` (12) in any case, and cornflow logs a warning at startup when
        these windows are inconsistent. ``POST /logout/`` closes a session, and the access tokens of a
        closed session stop working at once. Reusing a refresh token that has already been rotated
        closes the session and emits the audit event ``session.reuse_detected``. ``cornflow sessions
        purge`` deletes the expired and revoked sessions. At levels 1 and 2 the login returns a single
        token of ``TOKEN_DURATION`` hours (24 at level 1, as in version 1.3.9, and 8 at level 2).
        Service users always get a single token. The login response also returns ``last_login``, the
        date of the previous login.

    - Personal API keys
        A personal API key is a long-lived credential (``API_KEY_DURATION_DAYS``, 365) that every
        endpoint accepts instead of a session token, meant for unattended processes. It is generated
        with ``POST /user/api-key/`` from a full session (with a fresh TOTP code when the user has
        two-factor authentication and ``API_KEY_STEPUP_TOTP=1``, the default at level 3) or with
        ``cornflow users api_key -u <username>``, and revoked with ``DELETE /user/api-key/``. Each user
        has one active key: a new key replaces the previous one, which keeps working for
        ``API_KEY_ROTATION_GRACE_MINUTES`` (60), with no more scope than the new key; a leaked key is
        revoked at once with ``DELETE /user/api-key/``. A read-only key (``"scope": "read"``, or
        ``--read-only`` in the CLI) is refused on any request other than GET, HEAD and OPTIONS. A key
        can not be used to change passwords, two-factor authentication, API keys, users, roles or
        permissions. The account lock and the two-factor reset revoke the keys; a password change does
        not. ``cornflow tokens notify-expiry``, meant to run once a day, emails the owner and the
        platform administrators when a key is about to expire (``TOKEN_EXPIRY_NOTIFICATION_DAYS``,
        ``30,7,3,2,1``). ``PERSONAL_TOKEN_ENABLED=0`` turns off the endpoint (501). In Airflow,
        ``connect_to_cornflow`` uses the key in ``CORNFLOW_SERVICE_API_KEY``, when it is set, instead
        of logging in with the service user.

    - BI tokens
        ``BI_TOKEN_DURATION_DAYS`` sets how long a BI token lasts: 0 at levels 1 and 2, which issues
        tokens without expiration date as in version 1.3.9, and 90 days at level 3 (between 1 and 365),
        where a BI token without expiration date answers 401. BI tokens are issued with
        ``cornflow users bi_token -u <username>``, deprecated together with the BI tokens in favour of
        the read-only personal API keys, which can be revoked one by one and get expiry warnings, while
        a BI token can only be invalidated by changing ``SECRET_BI_KEY``.

        Breaking change: the ``cornflow users create token`` command has been removed. Use
        ``cornflow users bi_token -u <username>`` or, better, a read-only personal API key
        (``cornflow users api_key -u <username> --read-only``).

    - Platform roles and data isolation
        New roles for the platform operators: ``platform_viewer`` (901), ``platform_planner`` (902) and
        ``platform_admin`` (903), with the permissions of their client counterpart. Only a platform
        administrator grants or revokes platform roles, and granting one through the API asks for a
        fresh TOTP code when the administrator has two-factor authentication and
        ``PLATFORM_ROLE_STEPUP_TOTP=1`` (level 3). At every level, only the user or a platform
        administrator edits, deletes or resets the two-factor authentication of a user with a platform
        role (``PUT`` and ``DELETE /user/<id>/``, ``DELETE /user/<id>/mfa/``). Create these users with
        ``cornflow users create platform_viewer``, ``platform_planner`` or ``platform_admin``, or set
        ``CORNFLOW_PLATFORM_ADMIN_USER``, ``CORNFLOW_PLATFORM_ADMIN_EMAIL`` and
        ``CORNFLOW_PLATFORM_ADMIN_PWD`` before ``cornflow service init``. At levels 2 and 3 only
        platform administrators create users through ``/signup/``, manage roles, permissions, actions
        and API views and revoke the admin role; at level 1 client administrators keep doing it as in
        version 1.3.9, except on the platform roles. ``POST /roles/`` accepts an optional ``id``. The
        instances, executions and cases created by platform users are not visible to client users,
        client administrators included (``PLATFORM_DATA_ISOLATION=0`` turns it off), in the lists and
        by id; service users are exempt so that Airflow can solve them. An update made by a service
        user no longer changes the owner of the object.

        Breaking change: the role ids 900 to 999 are reserved for the platform roles. Role registration
        stops cornflow from starting if a custom role of an external application uses an id in that
        range, or if a stored role has a platform role id with another name: move those roles to an id
        between 5 and 899, or from 1000, before upgrading.

    - Password recovery
        With ``CORNFLOW_UI_URL`` set, the recovery email carries a single-use link to the web client
        (``<CORNFLOW_UI_URL>/reset-password?token=...``) valid for ``PWD_RESET_TOKEN_DURATION_MINUTES``
        (30), and the new password is set with ``PUT /user/reset-password/``. Without it the email
        still carries a temporary password, one-time from level 2.

    - Security audit log
        Security events are written as one JSON record per line on the ``cornflow.audit`` logger,
        separate from the application log: logins, account locks and unlocks, password changes, resets
        and recovery requests, two-factor enrollments and resets, API keys issued, revoked and about to
        expire, BI tokens issued, users created, roles granted and revoked and session events, from the
        API and from the CLI. Each record carries the time, the event and the outcome and, when known,
        the actor, the target and the source IP. ``AUDIT_LOG_ENABLED=0`` turns it off.

    - Rate limits
        Login, token refresh and logout are limited per client IP (``RATELIMIT_LOGIN``,
        ``10 per minute``) counting only the failed responses, so successful logins (also those of the
        Airflow tasks) never use the limit up. Password recovery and reset count every request
        (``RATELIMIT_RECOVER``, ``5 per hour``). Over the limit the endpoint answers 429. The counters
        are kept per process by default and cornflow logs a warning at startup: with several gunicorn
        workers set ``RATELIMIT_STORAGE_URI`` to a shared storage (Redis is supported). Behind a reverse
        proxy set ``RATELIMIT_TRUST_FORWARDED_FOR=1``, so that the limit counts each client IP and not
        the proxy; the IP is the right-most ``X-Forwarded-For`` entry, added by that proxy, also in the
        audit log. ``RATELIMIT_ENABLED=0`` turns the limits off.

    - Security headers, CORS and interactive API docs
        Every response carries security headers for browsers (``X-Content-Type-Options``,
        ``X-Frame-Options``, a deny-by-default ``Content-Security-Policy``, ``Referrer-Policy``,
        ``Permissions-Policy``, ``Cache-Control: no-store`` and, with ``HSTS_ENABLED=1``,
        ``Strict-Transport-Security``); the ``Server`` banner is overwritten and ``X-Powered-By`` is
        removed. cornflow-client, Airflow and the CLI are not affected. ``SECURITY_HEADERS_ENABLED=0``
        turns them off, and ``CONTENT_SECURITY_POLICY``, ``REFERRER_POLICY``, ``PERMISSIONS_POLICY``,
        ``SECURITY_NO_STORE`` and the ``HSTS_*`` variables adjust them. ``CORS_ORIGINS`` is now applied:
        ``*`` (levels 1 and 2) allows any origin, a comma-separated list restricts it and an empty value
        (level 3) closes it. With ``CORNFLOW_DOCS_ENABLED=1`` (the default at levels 1 and 2) the routes
        of the Swagger UI (the page, its static files and the OpenAPI schema) get a
        Content-Security-Policy of their own that lets the interface load and work in the browser, with
        no external resources; the rest of the API keeps the strict policy, or
        ``CONTENT_SECURITY_POLICY`` if it is set. ``CORNFLOW_DOCS_ENABLED=0`` (level 3) removes them.

    - Secret key
        The secret key signs the sessions, the personal API keys and the temporary tokens, and encrypts
        the two-factor secrets. ``FERNET_KEY`` is the recommended variable; ``SECRET_KEY`` is only an
        alternative, read when ``FERNET_KEY`` is not set. An empty variable counts as unset. The key is
        resolved in the configuration, so the server and the CLI sign with the same one. Levels 2 and 3
        do not start without a key of at least 32 bytes; at level 1 without a key, cornflow uses a
        random key generated once per start and shared by all the gunicorn workers, with a warning.
        A ``SECRET_BI_KEY`` shorter than 32 bytes stops levels 2 and 3 from starting and logs a warning
        at level 1. The documentation and the startup messages suggest generating the key with Fernet:
        ``python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"``
        prints 44 characters (32 random bytes) and the key is also valid for Airflow.

        Breaking change: when ``FERNET_KEY`` and ``SECRET_KEY`` are both set with different values,
        cornflow signs with ``FERNET_KEY`` and logs a warning, so a deployment that was signing with
        ``SECRET_KEY`` (for example, started with ``flask`` instead of ``cornflow service init``)
        closes its sessions unless both variables get the same value. ``cornflow service init`` no
        longer writes ``SECRET_KEY`` (it used to fill it with ``FERNET_KEY`` or with a new random key
        on every start): external applications that read ``SECRET_KEY`` on their own must have it set
        in their environment.

    - Invalid tokens
        Breaking change: at every level, an expired token, a token with a wrong signature or format
        (also from OpenID Connect), a revoked session or API key, the token of a user that no longer
        exists and an expired or invalid BI token answer 401 with the header
        ``WWW-Authenticate: Bearer error="invalid_token"``. Several of these cases answered 400 in
        version 1.3.9; cornflow-client 1.4 accepts both. Requests without a token, or with a header
        that does not follow ``Bearer <token>``, still answer 400.

    - Error messages
        The login and the sign-up no longer return internal exceptions to the client when the token
        can not be generated, and the decryption error of the stored secrets no longer names the secret
        key. A wrong password always gets the same generic error: the locked account message is only
        shown to whoever gives the correct password.

    - Plugins and routes
        The core endpoints are registered under ``/cornflow/`` (a Flask blueprint) and the routes
        without prefix are kept as aliases; the security checks and the rate limits apply equally to
        both, and the OpenAPI schema only documents the ``/cornflow/`` routes. With ``EXTERNAL_APP=0``
        cornflow loads the plugins published under the ``cornflow.plugins`` entry point group
        (``CornflowPlugin`` in ``cornflow.shared.plugins``), which mount their routes at the root. On
        every ``access_init`` cornflow keeps the views mounted by the plugins, calls the
        ``register_access`` of each plugin by ``priority`` and leaves the permissions on their views as
        their code declares them (``ROLES_WITH_ACCESS`` and ``get_custom_roles_actions``), deleting the
        ones added by hand. ``init_app`` runs in the order the entry points are discovered. A plugin that
        fails to load, or that mounts an endpoint name or a URL already used by cornflow or by another
        plugin, stops cornflow from starting with an error that names it. With ``EXTERNAL_APP=1``
        cornflow keeps working as an external application.

        Breaking change: ``APPLICATION_ROOT`` now only applies with ``EXTERNAL_APP=1``, where
        cornflow is mounted under it; in version 1.3.9 it only applied with ``EXTERNAL_APP=0``. A
        deployment with ``EXTERNAL_APP=0`` that served cornflow under a path other than ``/`` now
        serves it under ``/cornflow/`` and at the root.

    - DAGs and executions
        Two requests that register the same DAG permissions at the same time (for example the DAG that
        updates the registry and a deployment) no longer fail with 500: the duplicate is discarded.
        Saving the Airflow log of an execution no longer changes its state: ``PUT /dag/<id>/`` only
        sets the state when the request carries one or a solution, and cornflow-client sends the error
        state together with the log.

    - Default passwords
        ``cornflow service init`` and the Airflow initialization script keep the default passwords of
        version 1.3.9 for the admin and service users. They do not comply with the password policy of
        levels 2 and 3, where ``CORNFLOW_ADMIN_PWD`` and ``CORNFLOW_SERVICE_PWD`` must be set.

    - Docker and Helm
        The docker-compose files set a development-only ``FERNET_KEY`` and ``SECRET_BI_KEY``, include
        ``CORNFLOW_SECURITY_LEVEL`` commented out and set example passwords for the admin and service
        users that comply with the password policy; ``docker-compose.yml`` also carries
        ``RATELIMIT_STORAGE_URI`` commented out. The Helm chart generates ``FERNET_KEY`` and
        ``SECRET_BI_KEY`` in a Secret that is kept across upgrades (or uses an existing one with
        ``cornflow.keys.existingSecret``), adds ``CORNFLOW_SECURITY_LEVEL`` and requires Helm 3.5 or
        later. Numeric or boolean values in ``cornflow.env`` (for example ``CORNFLOW_SECURITY_LEVEL: 3``)
        no longer prevent the chart from rendering.

        Breaking change: the Helm chart no longer sets ``SECRET_KEY`` and fails to render if
        ``cornflow.env`` sets ``FERNET_KEY``, ``SECRET_KEY`` or ``SECRET_BI_KEY``: to keep the key in
        use, store it in a Secret and set ``cornflow.keys.existingSecret``. The example passwords of the
        admin and service users have changed in the docker-compose files and in ``values.yaml``, and
        existing users keep their password: a deployment that relied on the old example values must
        set ``CORNFLOW_SERVICE_PWD`` and the password of the Airflow connection to the one in use.

    - Other changes
        The CLI connects to ``DATABASE_URL`` first, so the commands run inside the container (for
        example ``cornflow users bi_token``) reach the same database as the server. A server UAT battery
        of the security controls (``test_uat_hardening_*.py``) runs at each security level. New
        dependencies: Flask-Limiter (with Redis support), pyotp and zxcvbn.

version 1.3.9
--------------
- released: 2026-10-19
- description: Airflow 3 support, automatic DAG permissions and security update
- changelog:
    - Airflow 3.2.2
        The Airflow image is upgraded from 2.9.1 to 3.2.2. The webserver is replaced by the
        api-server and a standalone dag-processor is now required. The Airflow client in
        cornflow-client detects the API version (v1 or v2) and authenticates with basic auth or
        JWT accordingly, so it keeps working against Airflow 2 deployments. Internal DAGs are
        adapted to Airflow 3 (no ORM access from tasks, ``schedule`` instead of
        ``schedule_interval``). A new ``airflow-k8s`` image and a Helm chart are provided.

    - DAG permissions
        Permissions are now created when a deployed DAG is registered or updated, without
        having to run the ``register_dag_permissions`` command. With ``OPEN_DEPLOYMENT=0``,
        admin users are granted access to every DAG along with service users. Fixed a case
        where a single new permission was not saved.

    - Security update
        Upgrade PyJWT to 2.15.1, cryptography to 50.0.2, requests to 2.33.0 and setuptools
        to 83.0.0.

version 1.3.8
--------------
- released: 2026-09-25
- description: Bug fixes
- changelog:
    - Bulk update and soft deleted rows
        Resending a row that had been soft deleted through a bulk update now reactivates it: its
        `deleted_at` is cleared and the update is applied, so the record becomes visible again on the
        reads. Previously the row was updated in place but stayed deleted, while the call answered
        201. If no row matches on the unique fields but the payload carries the `id` of a soft deleted
        row, that row is reactivated instead of failing on the primary key. Models without soft delete
        keep the previous behaviour.

    - Databricks backend configuration
        When the Databricks backend is selected, the required environment variables
        (DATABRICKS_HOST, DATABRICKS_CLIENT_SECRET, DATABRICKS_TOKEN_ENDPOINT, DATABRICKS_EP_CLUSTERS,
        DATABRICKS_CLIENT_ID) are validated on startup, and a clear fatal error lists the missing ones.
        DATABRICKS_HEALTH_PATH defaults to "default path" when not set.

    - Emails
        Fixed the email body being attached twice, which made some clients render it twice or flag
        the message as malformed.

version 1.3.7
--------------
- released: 2026-07-10
- description: Performance improvement
- changelog:
    - Improve performance of executions endpoint
    - Add bug fix for when using click 8.4.0 with celery executor

version 1.3.6
--------------
- released: 2026-06-25
- description: Security update and performance improvement
- changelog:
    - Upgrade cryptography to 48.0.1 and PyJWT to 2.13.0
    - Improve performance of executions endpoint

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