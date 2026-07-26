Access control
-----------------------

cornflow supports multi-user access using password encryption authentication. The user needs to authenticate at least once with the cornflow server to obtain a token that allows him to continue operating.
In this section we will explain the workflow and data process when create users, delete them or change the user´s access password.

User access data
*********************

Right now cornflow has two valid user authentication methods. The first is AUTH_DB, which in addition to being the one that is activated by default, is the easiest to configure since the authentication is carried out against the application itself that stores the credentials in encrypted form.
The second method is AUTH_LDAP. This method allows you to link cornflow with your own security directory and thus the application will delegate the authentication of the users.

With Auth-DB (default)
^^^^^^^^^^^^^^^^^^^^^^^^^

cornflow has an environment variable to control the type of authentication we want to activate::

    AUTH_TYPE = 1 (Auth-DB default method)

User datatable default content::

    user name
    password
    first name
    last name
    email
    admin-super admin (deprecated)
    auditory fields (cornflow saves information such us the date of creation or modification of the user)

The password is stored encrypted in the database. If a user does not have a password an email will be sent with the temporary access password.

With Auth-LDAP
^^^^^^^^^^^^^^^^^

As we saw previously cornflow has an environment variable to control the type of authentication we want to activate::

    AUTH_TYPE = 2 (Auth-LDAP authentication)

This authentication will be through a unique user code "common name" (user name) and password. The password will never be stored on the cornflow server but other data will be stored that will allow users to migrate or import to change the type of authentication. This operation cannot be performed with the server running.
In the event that you consult the connection through LDAP, the following information will be requested from the server.,

User datatable default content::

    user name
    email
    auditory fields - (cornflow saves information such us the date of creation or modification of the user)

User data objects request from LDAP server::

    password validation (only for compare)
    email
    role

No password is stored in the database. No confirmation email is sent with a temporary access password.

**LDAP authentication library**

In cornflow we have used `this library <https://github.com/tedivm/tedivms-flask>`_ to develop authentication methods. With this configuration the cornflow backend will be connected to external LDAP server:

Any installation can run with Auth-LDAP as its backend with these settings::

    LDAP_HOST - ldap server address 
    LDAP_BIND_DN - ldap admin search for domain
    LDAP_BIND_PASSWORD - ldap admin search password
    LDAP_USERNAME_ATTRIBUTE - The name of the attribute that represents the unique ID of the user
    LDAP_USER_BASE - The base DN subtree that is used when searching for user entries on the LDAP server
    LDAP_USER_OBJECT_CLASS - The object classes are defined in the LDAP directory schema (they constitute a class hierarchy there)
    LDAP_GROUP_OBJECT_CLASS - Filter used for returning a list of group member entries that are in the LDAP base DN (groups) subtree
    LDAP_GROUP_ATTRIBUTE - The name of the attribute in the group search filter that represents the group name
    LDAP_GROUP_BASE - The base DN subtree that is used when searching for group entries on the LDAP server
    LDAP_USE_TLS - TLS communication protocol (Transport Layer Security) over 636 port
    LDAP_EMAIL_ATTRIBUTE - ldap email user object

Password policy and hardening (CCN-STIC-807)
************************************************

For internal (Auth-DB) users cornflow enforces a hardened password policy
aligned with the CCN-STIC-807 guidelines. A password must:

* Have at least 12 characters (``PWD_MIN_LENGTH``, default 12).
* Contain at least one lowercase letter, one uppercase letter, one number
  and one special character, and no whitespace.
* Not contain sequences of 6 or more digits (dates, phone numbers...).
* Not contain the username, first name, last name or email of the user.
* Reach a minimum strength score computed with `zxcvbn
  <https://github.com/dropbox/zxcvbn>`_, which rejects common, leaked and
  predictable passwords while allowing long passphrases
  (``PWD_MIN_ZXCVBN_SCORE``, default 3 out of 4).

Additionally:

* The last passwords of each user are remembered (hashed) and can not be
  reused (``PWD_HISTORY_SIZE``, default 10).
* When a user changes their own password they must provide the current one,
  and the new password can not be a trivial variation of it
  (``PWD_MAX_SIMILARITY``, default 0.8 similarity ratio).
* Passwords expire after ``PWD_ROTATION_TIME`` days (default 120). When
  ``PWD_ROTATION_ENFORCE`` is set to 1 (the default), a user whose password
  has expired (or was reset by an admin or the recovery email) can only
  access the endpoints needed to change it: every other endpoint answers
  403 with ``error_code: password_rotation``.
* Passwords set by an administrator or generated by the password recovery
  email are temporary: the user is forced to change them at the next login.
* Password recovery: when ``CORNFLOW_UI_URL`` is configured (the base URL of
  the web client), the recovery email contains a **reset link** pointing to
  ``<CORNFLOW_UI_URL>/reset-password?token=...``. The token is signed,
  valid for ``PWD_RESET_TOKEN_DURATION_MINUTES`` (default 30, capped at
  60), only grants access to the reset endpoint (``PUT
  /user/reset-password/``) and becomes unusable as soon as the password
  changes (single use). When ``CORNFLOW_UI_URL`` is not set (API-only
  deployments) the email falls back to a temporary password that must be
  changed at the next login. The response of the recovery endpoint is the
  same whether the email exists or not, so accounts can not be enumerated.

Service users (SERVICE role) are exempt from rotation enforcement and
two-factor authentication, as they are machine-to-machine accounts (e.g.
the cornflow-airflow communication user), but their passwords must comply
with the pattern policy. LDAP and OpenID users are not affected: their
credential policies belong to the external identity provider.

The security configuration values (password policy thresholds, token
duration, rotation time, lockout parameters) are clamped to minimum
security floors or ceilings: even if the environment variables are
tampered with, the policy can not be weakened below the CCN-STIC-807
thresholds (e.g. ``PWD_MIN_LENGTH`` can never go below 12 and
``TOKEN_DURATION`` never above 24 hours; the session token duration
defaults to 8 hours). In addition, the server refuses to start when
``SECRET_KEY`` or ``SECRET_BI_KEY`` are shorter than 32 bytes (256 bits,
as required by RFC 7518 for HMAC-SHA256); generate them with::

    python -c "import secrets; print(secrets.token_hex(32))"

Session revocation: security events invalidate every outstanding session
token of the affected user immediately (the tokens carry a version claim
that is checked on each request). A password change (own, by an admin or
through the recovery email), an account lock and a two-factor
authentication reset all revoke the user's sessions, which then answer
401 and require a new login. BI tokens are excluded (they are long-lived
by design and signed with a separate key).

Per-IP rate limiting: the login, password recovery and password reset
endpoints are rate limited per client IP, on top of the per-account
lockout. This throttles password spraying (many usernames from one source)
and abuse of the recovery endpoint to flood inboxes. Limits are
configurable (``RATELIMIT_LOGIN`` default ``10 per minute``,
``RATELIMIT_RECOVER`` default ``5 per hour``); over the limit the endpoint
answers 429. The counters use an in-memory backend by default, which is
per-process: a production deployment behind several gunicorn workers must
set ``RATELIMIT_STORAGE_URI`` to a shared backend (e.g. ``redis://...``).
When behind a reverse proxy, set ``RATELIMIT_TRUST_FORWARDED_FOR=1`` so the
real client IP (from ``X-Forwarded-For``) is used instead of the proxy's;
leave it off on direct deployments so the header can not be spoofed. The
whole feature can be disabled with ``RATELIMIT_ENABLED=0``.

Account lockout: after ``LOGIN_MAX_ATTEMPTS`` (default 5, capped at 10)
consecutive failed login attempts — wrong password or wrong two-factor
code — the account is locked. While locked, the login endpoint answers 403
with ``error_code: account_locked`` even if the correct credentials are
provided. The lock does not expire: only a **platform administrator** (the
``platform_admin`` role) can unlock the account through
``PUT /user/<id>/unlock/``, or an operator with shell access through the
break-glass command ``cornflow users unlock -u <username>``. A successful
login resets the failure counter. Service users are exempt from the
lockout (so the platform communication can not be denial-of-serviced by
targeting a well-known account name), but their failed attempts are logged
as warnings. Platform administrator users can be created with
``cornflow users create platform_admin``.

.. warning::
   The default values of ``CORNFLOW_ADMIN_PWD`` and ``CORNFLOW_SERVICE_PWD``
   do not comply with this policy (they contain the username). New
   deployments must provide their own compliant values or the initial user
   creation will fail with a clear error in the logs.

Two-factor authentication (TOTP)
************************************

Internal users authenticate with a second factor based on TOTP (RFC 6238),
compatible with any authenticator app (Google Authenticator, Microsoft
Authenticator, Aegis, FreeOTP...). No external service is involved: the
secret is generated by cornflow, stored encrypted at rest and verified
locally.

* ``MFA_REQUIRED`` (default 1): when active, every internal non-service
  user must enroll. The login of a user without MFA returns
  ``mfa_setup_required`` and a short-lived enrollment token
  (``MFA_SETUP_TOKEN_DURATION_MINUTES``, default 10) that is only valid on
  the enrollment endpoints.
* Enrollment: ``POST /mfa/setup/`` returns the secret and the
  ``otpauth://`` provisioning URI (to render a QR code);
  ``POST /mfa/verify/`` with the first code activates MFA, returns the
  one-time backup codes (``MFA_BACKUP_CODES_NUMBER``, default 8) and a full
  session token.
* Login with MFA: ``POST /login/`` with ``username`` and ``password``
  returns ``mfa_required`` when the code is missing; sending ``totp_code``
  (a TOTP code or an unused backup code) returns the session token.
* Reset: ``DELETE /user/<id>/mfa/`` (the user themselves or an admin, e.g.
  when a phone is lost). With ``MFA_REQUIRED=1`` the user will enroll again
  at the next login.

BI tokens
************

BI tokens are long-lived tokens for BI tools (e.g. Power BI) signed with a
separate key (``SECRET_BI_KEY``). They are no longer permanent: they expire
after ``BI_TOKEN_DURATION_DAYS`` days (default 90, capped at 365) and are
excluded from the per-request session-revocation check. Regenerate one from
inside the server (where the CLI has database access) with::

    cornflow users bi_token -u <username>

This command needs no further authentication because CLI/shell access is
already privileged; the generation is logged.

.. note::
   Running the cornflow CLI inside the container requires it to reach the
   same database as the server. The CLI now honours ``DATABASE_URL`` first
   (the same variable the server uses), so as long as ``DATABASE_URL`` is set
   in the container environment, commands such as ``cornflow users bi_token``
   connect correctly. Previously the image forced ``DEFAULT_POSTGRES=1``,
   which made the CLI rebuild the URL from the ``CORNFLOW_DB_*`` defaults and
   fail to connect. Token generation additionally needs ``SECRET_KEY`` and
   ``SECRET_BI_KEY`` present in the container environment (set them
   explicitly; do not rely on a value generated at startup, which is not
   available to a later ``docker exec`` session and would also prevent
   decrypting stored MFA secrets across restarts).

Personal API keys
********************

A personal API key is a long-lived bearer token (default 1 year,
``API_KEY_DURATION_DAYS``, capped at 2 years) that authenticates the API as
an alternative to the short-lived session JWT — every endpoint accepts
either credential. It is meant for unattended automation.

- **Minted behind full authentication.** It is issued only on a full
  session; when the user has MFA enabled the server requires a fresh TOTP
  step-up (``API_KEY_STEPUP_TOTP``, on by default). It can be generated from
  the web client (Settings), the ``cornflow-client`` library
  (``create_api_key()`` after ``login``), or the CLI
  (``cornflow users api_key -u <username>``, trusted by machine access — no
  TOTP). Shown only once.
- **One active key per user.** Generating a new key revokes the previous
  one; it is also revoked explicitly (``DELETE /user/api-key/`` or the
  Settings screen), and automatically on account lock and MFA reset. A
  routine password change does NOT revoke it (automation continuity).
- **Not for account management.** An API key can not reach the
  security-sensitive endpoints (password change, MFA, API key
  management, user/role administration): a leaked key can not escalate.
- **Disable per deployment** with ``PERSONAL_TOKEN_ENABLED=0`` (the Settings
  section is hidden and the endpoint returns 501).

Service users can hold an API key too. Because the cornflow↔airflow service
connection otherwise re-logs in with the service password on every task
(and the session token now expires in 8 h), the recommended setup is to
generate a key for the service user (``cornflow users api_key -u
service_user``) and expose it to Airflow as ``CORNFLOW_SERVICE_API_KEY``:
``connect_to_cornflow`` then uses the long-lived key and skips the per-task
login. Rotate it yearly (regenerate + update the variable).

Security audit log
*********************

Security-relevant events are emitted as structured JSON records on a
dedicated logger (``cornflow.audit``), separate from the application log, so
a log pipeline / SIEM can collect and retain them. Each record is a single
JSON object per line, for example::

    {"ts": "2026-07-26T09:14:02.511+00:00", "audit": true, "event": "login.success", "outcome": "success", "actor_id": 42, "actor": "jdoe", "ip": "10.0.3.7", "method": "db"}
    {"ts": "2026-07-26T09:16:10.882+00:00", "audit": true, "event": "account.locked", "outcome": "locked", "target_id": 42, "target": "jdoe", "attempts": 5}

Every record carries a UTC ``ts`` timestamp, the ``audit`` marker (for easy
filtering), the ``event`` name and its ``outcome``; the actor, target, source
IP and event-specific fields are added when known. Inside a request the actor
and IP are filled in automatically; from the CLI the ``source`` is ``cli``.
The events covered include ``login.success`` / ``login.failure``,
``account.locked`` / ``account.unlocked``, ``password.changed`` /
``password.reset`` / ``password.recovery_requested``, ``mfa.enrolled`` /
``mfa.reset``, ``apikey.issued`` / ``apikey.revoked``, ``bitoken.issued`` and
``role.granted`` / ``role.revoked``.

The failed-login records may name the attempted (even non-existent) username:
this is intentional and useful to defenders because the audit channel is a
trusted internal sink. The client-facing responses stay generic and never
reveal whether a username or email exists.

This is the emission layer only. Collection, append-only retention, host time
synchronisation and alerting are the responsibility of the deployment's log
pipeline / SIEM (e.g. ship stdout to Loki / ELK / CloudWatch and alert on
repeated ``account.locked`` or ``apikey.issued`` bursts). Auditing can be
turned off with ``AUDIT_LOG_ENABLED=0`` (on by default).

Web security headers and CORS
********************************

Every response carries a set of HTTP security headers (added by a single
``after_request`` hook). These are instructions to **browsers** only — the
``cornflow-client`` library, Airflow and the CLI ignore them, so the
machine-to-machine paths are unaffected.

* ``X-Content-Type-Options: nosniff`` — no MIME sniffing.
* ``X-Frame-Options: DENY`` and a ``frame-ancestors 'none'`` CSP — no framing
  (clickjacking).
* ``Content-Security-Policy: default-src 'none'; frame-ancestors 'none';
  base-uri 'none'`` — deny-by-default; the API returns JSON and the docs UI is
  off in production, so nothing needs to load. Override with
  ``CONTENT_SECURITY_POLICY`` if you re-enable the docs.
* ``Referrer-Policy: no-referrer`` — do not leak URLs (which may carry tokens,
  e.g. the password reset link) through the ``Referer`` header.
* ``Permissions-Policy`` — disables browser features the app does not use.
* ``Cache-Control: no-store`` — responses carry auth data and should not be
  cached (``SECURITY_NO_STORE=0`` to disable).
* The ``Server`` banner is overwritten and ``X-Powered-By`` removed to reduce
  version fingerprinting.

The whole set can be turned off with ``SECURITY_HEADERS_ENABLED=0``.

.. warning::
   **HSTS** (``Strict-Transport-Security``) is **on by default in production**
   (``HSTS_ENABLED``; ``max-age`` one year, ``includeSubDomains``). Only serve
   the header once TLS terminates in front of cornflow: a browser that has
   seen it will refuse plain HTTP afterwards. If TLS is not yet in place, set
   ``HSTS_ENABLED=0`` until it is. ``HSTS_PRELOAD`` is off by default (opting
   into the preload list is hard to reverse).

**CORS** is driven by ``CORS_ORIGINS``:

* development default ``*`` (any origin),
* **production default is empty — default-closed**: set ``CORS_ORIGINS`` to
  the web client origin(s), comma-separated (e.g.
  ``https://cornflow.example.com``), or the SPA will be unable to call the API
  from the browser.

Because authentication uses a Bearer token in the ``Authorization`` header
(not a cookie), classic CSRF is already mitigated; the CORS lock-down is
defense-in-depth and closes the previously wide-open ``*`` policy.

**Interactive API docs** (Swagger UI at ``/swagger-ui/`` and the OpenAPI
schema at ``/swagger/``) are **disabled in production** by default
(``CORNFLOW_DOCS_ENABLED=0``) to shrink the attack surface and keep the strict
CSP. Re-enable with ``CORNFLOW_DOCS_ENABLED=1`` (you will likely also need to
relax ``CONTENT_SECURITY_POLICY`` so the Swagger UI assets load).

Roles definition
*********************

In cornflow there is a differentiation between user roles with different characteristics::

    Platform admin - platform operator: superset of the client admin. It is the only role that can manage roles and permissions (roles, permission, apiview and action endpoints), unlock locked accounts and revoke the admin role from a user
    Admin - client administrator: manages the users of their own deployment (create/disable users, assign roles, manage DAG access) but can not manage the permission model nor revoke admin from another admin
    Service - service user role reserved for service accounts (cornflow and airflow communication)
    Viewer - read only user
    Planner - the general user of cornflow can create jobs and send models to solve

The split between platform admin and client admin: a client admin runs the
day-to-day of their deployment (users, role assignment, DAG access) but can
not reshape the security model. The roles, permissions, apiview and action
endpoints require the platform_admin role; so does unlocking an account and
revoking the admin role from a user (a client admin can grant admin but only
a platform admin can take it away). The platform admin inherits every
client-admin permission on top of the platform-only ones.

.. warning::
   A fresh deployment needs at least one platform administrator to manage
   roles and unlock accounts. Provision one with
   ``cornflow users create platform_admin`` (or set the
   ``CORNFLOW_PLATFORM_ADMIN_USER`` / ``CORNFLOW_PLATFORM_ADMIN_EMAIL`` /
   ``CORNFLOW_PLATFORM_ADMIN_PWD`` variables before the service init).

Each role is stored in a table linking the role code with the permissions on the application.
In addition, there is a temporary link between the user and his role that will not be updated until the login operation is performed again.

**User role assignation (in all authentication types)**

In this table we have the role assignment for each user. May be more than one role assigned to the user.

Data storage::

    User ID - internal cornflow user identification 
    Role ID assigned - role identification assigned to the user

**Role data storage (in all authentication types)**

Master data of roles in application::

    Role ID - internal cornflow role identification
    Role name - role name

Roles with Auth-LDAP
^^^^^^^^^^^^^^^^^^^^^^^^

In the cornflow server deployment, the LDAP server roles will be configured through environment variables. cornflow roles to bind to ldap server::

    LDAP_GROUP_TO_ROLE_SERVICE
    LDAP_GROUP_TO_ROLE_ADMIN 
    LDAP_GROUP_TO_ROLE_VIEWER
    LDAP_GROUP_TO_ROLE_PLANNER

In this way, the user permissions and their defined roles are always done within the cornflow application and allow the authentication configuration to be changed in the future.

cornflow interactions with airflow (service user)
*****************************************************

cornflow ⇒ Airflow
^^^^^^^^^^^^^^^^^^^^^^

Not all cornflow users can access airflow. A role defined in the application will give access to perform actions that involve communication with airflow through the user defined in the previous point.
If the user has access to airflow, in each communication, the username and password that provides access to the platform will be provided by this environment variables::

    AIRFLOW_USER - airflow user name for login in airflow and manage dags
    AIRFLOW_PWD - airflow user password

Airflow does not have to be connected via LDAP. Linking them does not affect how cornflow works. Airflow receives a username and password that has privileges to perform actions defined in the system by cornflow.
The cornflow user profile in airflow must have the following permissions::

    administrate connections
    administrate DAG
    administrative Tasks
    administrate DAG Runs
    administrator Jobs

If airflow also connects through LDAP to the same active directory, it will be necessary in the deployment configuration to bind the user that communicates cornflow with the role that gives the previously defined permissions.
The user who operates airflow through cornflow may not be the same user who has the role of system administrator of the platform.

**User access to dags**

The user access to each dag in airflow can be controlled in cornflow. cornflow store a table with dags and have roles that give access to each dag individually.

Airflow ⇒ cornflow
^^^^^^^^^^^^^^^^^^^^^^^

Airflow use a cornflow service rights that allow it to do some operations. It´s used to get and post to any user’s instances and executions. In this way this role restrict for doing admin stuff (e.g., manage users or delete them)
Service user is a good solution for doing all the data interaction between applications. You have only to pay attention to one account for set permissions and key values on deployment::

    CORNFLOW_SERVICE_USER - service user account name for communications between cornflow and airflow (default value `service_user`)
    CORNFLOW_SERVICE_MAIL - service user account email (default value `service_user@cornflow.com`)
    CORNFLOW_SERVICE_PWD - service user account password (default value `Service_user1234`)

This connection is provided by::

    AIRFLOW_CONN_CF_URI="cornflow://CORNFLOW_SERVICE_USER:CORNFLOW_SERVICE_PWD@cornflowserveraddress:cornflowserverport"

Keep in mind to change default credentials when going to production.

Manage cornflow users
***********************

In the cornflow image, if no environment variables are set, an admin user is created with these credentials::

    CORNFLOW_ADMIN_USER - cornflow_admin
    CORNFLOW_ADMIN_EMAIL - cornflow_admin@cornflow.com
    CORNFLOW_ADMIN_PWD - Cornflow_admin1234

It is advisable to change the default admin user and keep the password in a safe place.

To create a user, you must interact with the cornflow application through an `endpoint of its API <https://baobabsoluciones.github.io/cornflow/dev/endpoints.html#module-cornflow.endpoints.user>`_. Check the API docs for the users `here <https://baobabsoluciones.github.io/corn/stable-rest-api-ref.html#tag/Users>`_. It is only possible to create new cornflow admin user using another one with those privileges.

Manage airflow users
***********************

The default administrator user for airflow and flower will be::

    AIRFLOW_USER - admin
    AIRFLOW_PWD - admin

It is advisable to change the default admin user and keep the password in a safe place.
`Access Control of Airflow Webserver UI <https://airflow.apache.org/docs/apache-airflow/stable/security/access-control.html>`_ is handled by Flask AppBuilder (FAB). Please read its related security document regarding its `security model <http://flask-appbuilder.readthedocs.io/en/latest/security.html>`_.

Remember to configure all authentication, users and access before passing to production. Check the previous section for more information: :ref:`Production deployment and security`.

External LDAP authentication server requirements
****************************************************

The requirements to communicate cornflow with an LDAP server are the following::

    An authentication server with support for the LDAPv3 protocol.
    The LDAP server must be visible at all times on the network by the cornflow server.
    The users created in the LDAP server must have unique identifiers and roles defined to relate them to the existing ones in cornflow.
    All users must have a unique user identifier and the password protocol will be the one provided by the LDAP authentication system.
    Users must have a field to store the email.
    The type of LDAP object used to search for users (objectClass)

For example, here are some example values for each of the ldap_user_type object::

        (objectClass=posixAccount) for RFC-2037 and RFC-2037bis
        (objectClass=sambaSamAccount) for SAMBA 3.0.x LDAP extension
        (objectClass=user) for MS-AD
        (objectClass=*) for Default
