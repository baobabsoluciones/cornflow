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

The password rules for internal (Auth-DB) users depend on the security
level (see :ref:`Security levels`).

At **level 1** cornflow applies the rules of version 1.3.9: at least
``PWD_MIN_LENGTH`` characters (default 5), uppercase and lowercase letters,
and at least one number and one special character. The zxcvbn score is
only checked if ``PWD_MIN_ZXCVBN_SCORE`` is set above 0. Previous passwords
are stored but their reuse is not checked, ``current_password`` is not
required and no password is one-time.

At **levels 2 and 3** cornflow enforces a hardened password policy aligned
with the CCN-STIC-807 guidelines. A password must:

* Have at least 12 characters (``PWD_MIN_LENGTH``, default 12, at
  least 12).
* Contain at least one lowercase letter, one uppercase letter, one number
  and one special character, and no whitespace.
* Not contain sequences of 6 or more digits (dates, phone numbers...).
* Not contain the username, first name, last name or email of the user.
* Reach a minimum strength score computed with `zxcvbn
  <https://github.com/dropbox/zxcvbn>`_, which rejects common, leaked and
  predictable passwords while allowing long passphrases
  (``PWD_MIN_ZXCVBN_SCORE``, default 3 out of 4, at least 3).

Additionally, at levels 2 and 3:

* The last passwords of each user are remembered (hashed) and can not be
  reused (``PWD_HISTORY_SIZE``, default 10, at least 10).
* When a user changes their own password they must provide the current one,
  and the new password can not be a trivial variation of it
  (``PWD_MAX_SIMILARITY``, default 0.8 similarity ratio, at most 0.9).
* Passwords set by an administrator (also when an administrator signs up a
  user) or generated by the password recovery email are one-time: the user
  must change them at the next login. So must the users flagged by the
  migration ``b7a1c9d807e5`` or created with ``--force-password-change``.
  Until then every other endpoint answers 403 with ``error_code:
  password_rotation``.

At every level:

* Passwords expire after ``PWD_ROTATION_TIME`` days (default 120, at most
  365 at level 3). The login response carries ``change_password: true``
  when the password is older than that (and, at levels 2 and 3, when it is
  flagged). With ``PWD_ROTATION_ENFORCE=1``, the default at level 3, a user
  whose password has expired can only access the endpoints needed to
  change it: every other endpoint answers 403 with ``error_code:
  password_rotation``. At levels 1 and 2 the expiry is only a warning.
* Password recovery: when ``CORNFLOW_UI_URL`` is configured (the base URL of
  the web client), the recovery email contains a **reset link** pointing to
  ``<CORNFLOW_UI_URL>/reset-password?token=...``. The token is signed,
  valid for ``PWD_RESET_TOKEN_DURATION_MINUTES`` (default 30, at most 60 at
  level 3), only grants access to the reset endpoint (``PUT
  /user/reset-password/``) and becomes unusable as soon as the password
  changes (single use). When ``CORNFLOW_UI_URL`` is not set (API-only
  deployments) the email falls back to a temporary password (one-time from
  level 2). The response of the recovery endpoint is the
  same whether the email exists or not, so accounts can not be enumerated.
* Keep ``PWD_MIN_LENGTH`` at 26 or below: the temporary passwords generated
  by the password recovery have at most 26 characters and always follow
  the policy of levels 2 and 3, so with a higher minimum the recovery
  request never finishes.

Service users (SERVICE role) are exempt from rotation enforcement and
two-factor authentication, as they are machine-to-machine accounts (e.g.
the cornflow-airflow communication user), but their passwords must comply
with the password rules of the level. LDAP and OpenID users are not affected: their
credential policies belong to the external identity provider.

The limits of the security settings depend on the level (see
:ref:`Limits by security level`): at levels 2 and 3 the password policy, the
lockout and the session duration can not be weakened below the
CCN-STIC-807 thresholds, while level 1 only keeps bcrypt at 12 rounds or
more. The secret keys are described in :ref:`Secret key (FERNET_KEY)`.

Session revocation: security events invalidate every outstanding session
token of the affected user immediately (the tokens carry a version claim
that is checked on each request). A password change (own, by an admin or
through the recovery email), an account lock and a two-factor
authentication reset all revoke the user's sessions, which then answer
401 and require a new login. BI tokens are excluded (they are long-lived
by design and signed with a separate key).

Per-IP rate limiting: the login, token refresh and logout endpoints
(``RATELIMIT_LOGIN``, default ``10 per minute``) count only the
failed responses (status 400 or above) of each client IP, so successful logins,
including those of the Airflow tasks, never use up the limit. The logout
always answers 200, so in practice it never counts. The password recovery
and reset endpoints (``RATELIMIT_RECOVER``, default ``5 per hour``) count
every request. Over the limit the endpoint answers 429, even with valid
credentials, until the window ends. This throttles password spraying (many
usernames from one source) and abuse of the recovery endpoint to flood
inboxes. It is not the account lockout: the lockout counts the consecutive
failures of each account, whatever the IP, and does not expire, while the
rate limit counts the failures of each IP, whatever the user, and expires
with its window; they complement each other. Because the counter is
checked before the request and only increased after a failed response, a
burst of simultaneous failed requests from one IP can go slightly over the
limit; the account lockout still protects each account.
The counters use an in-memory backend by default, which is
per-process: a production deployment behind several gunicorn workers must
set ``RATELIMIT_STORAGE_URI`` to a shared backend (e.g.
``redis://<host>:6379/0``; the Redis client is installed with cornflow).
With ``memory://`` every worker keeps its own counters (the image starts
three), so a client is only throttled after the configured limit times the
number of workers and the ``X-RateLimit-Remaining`` header goes up and down
depending on the worker that answers. The server logs a warning at startup
when rate limiting is on and the storage is ``memory://``. The Helm chart
(``RATELIMIT_STORAGE_URI`` in ``values.yaml``) and ``docker-compose.yml``
carry the variable, commented, ready to point to a Redis.
When behind a reverse proxy, set ``RATELIMIT_TRUST_FORWARDED_FOR=1`` so the
real client IP (from ``X-Forwarded-For``) is used instead of the proxy's;
leave it off on direct deployments so the header can not be spoofed. The
whole feature can be disabled with ``RATELIMIT_ENABLED=0``.

Account lockout: when ``LOGIN_MAX_ATTEMPTS`` is greater than 0 (5 at levels
2 and 3, where it must be between 1 and 10), the account is locked after
that number of consecutive failed login attempts — wrong password or wrong
two-factor code. At level 1 the default is 0: there is no lockout and
failed attempts are not counted; a value above 0 turns the lockout on at
level 1 too. While locked, the login endpoint answers 403 with
``error_code: account_locked`` (``The account is locked due to too many
failed login attempts. Please contact an administrator to unlock it.``)
when the correct password is given; a wrong password still gets the
generic 400. The lock does not expire. It revokes every session and
personal API key of the user, including a superseded key still in its
rotation grace window, and emits a single ``account.locked`` audit event.
Accounts locked earlier stay locked, whatever the level or
``LOGIN_MAX_ATTEMPTS``, until someone unlocks them. Through
``PUT /user/<id>/unlock/``, at levels 1 and 2 a platform administrator can
unlock any account and a client administrator only the accounts of users
without a platform role (403 otherwise); at level 3 only a platform
administrator can. At any level an operator with shell access can use the
break-glass command ``cornflow users unlock -u <username>``. A successful
login resets the failure counter. Service users are exempt from the
lockout (so the platform communication can not be denial-of-serviced by
targeting a well-known account name), but their failed attempts are logged
as warnings. Platform administrator users can be created with
``cornflow users create platform_admin``.

.. warning::
   The default values of ``CORNFLOW_ADMIN_PWD`` (``Cornflow_admin1234``) and
   ``CORNFLOW_SERVICE_PWD`` (``Service_user1234``) are those of 1.3.9: they
   follow the rules of level 1 but not the policy of levels 2 and 3. At
   levels 2 and 3, set compliant values before the users are created, or
   cornflow does not start (the log names the user and the reason). The
   ``docker-compose`` files and the Helm chart set their own explicit
   values, which comply with the policy.

Two-factor authentication (TOTP)
************************************

Internal users can authenticate with a second factor based on TOTP (RFC 6238),
compatible with any authenticator app (Google Authenticator, Microsoft
Authenticator, Aegis, FreeOTP...). No external service is involved: the
secret is generated by cornflow, stored encrypted at rest and verified
locally.

* Users can only enroll when ``MFA_ENABLED=1``, the default at level 3 (see
  :ref:`Two-factor enrollment (MFA_ENABLED)`).
* ``MFA_REQUIRED`` (0 at levels 1 and 2, 1 at level 3; it needs
  ``MFA_ENABLED=1``): when active, every internal non-service
  user must enroll. The login of a user without MFA returns
  ``mfa_setup_required`` and a short-lived enrollment token
  (``MFA_SETUP_TOKEN_DURATION_MINUTES``, default 10, at most 30 at level 3) that is only valid on
  the enrollment endpoints.
* Enrollment: ``POST /mfa/setup/`` returns the secret and the
  ``otpauth://`` provisioning URI (to render a QR code);
  ``POST /mfa/verify/`` with the first code activates MFA, returns the
  one-time backup codes (``MFA_BACKUP_CODES_NUMBER``, default 8, at most 20 at level 3) and a full
  session token.
* Login with MFA: ``POST /login/`` with ``username`` and ``password``
  returns ``mfa_required`` when the code is missing; sending ``totp_code``
  (a TOTP code or an unused backup code) returns the session token.
* Reset: ``DELETE /user/<id>/mfa/`` (the user themselves or an admin, e.g.
  when a phone is lost). It revokes every session and the personal API key
  of the user, including a superseded key still in its rotation grace
  window, as the account lock does. With ``MFA_REQUIRED=1`` the user will
  enroll again at the next login.

BI tokens (deprecated)
*************************

.. warning::
   BI tokens are **deprecated** in favour of the **read-only personal API
   keys** described above: those are individually revocable, expire per user,
   can be renewed from the web client and get expiry notifications, while a BI
   token can only be invalidated by rotating ``SECRET_BI_KEY`` — which
   invalidates every BI token at once. They are kept for backwards
   compatibility with deployments and external applications whose endpoints
   still authenticate with ``BIAuth``; migrate those to ``Auth`` and issue
   ``cornflow users api_key -u <user> --read-only`` instead. Support will be
   removed in a future release.

BI tokens are long-lived tokens for BI tools (e.g. Power BI) signed with a
separate key (``SECRET_BI_KEY``). They last ``BI_TOKEN_DURATION_DAYS``
days: 0 at levels 1 and 2, which issues tokens without expiration date (as
in 1.3.9), and 90 at level 3, where it must be between 1 and 365 and a
token without expiration date is rejected with 401 (see
:ref:`Raising the security level`). They are excluded from the
per-request session-revocation check. Regenerate one from inside the
server (where the CLI has database access) with::

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
   fail to connect. Token generation additionally needs the secret keys in the
   container
   environment: ``FERNET_KEY`` (or ``SECRET_KEY``) for personal API keys
   and session tokens, and ``SECRET_BI_KEY`` for BI tokens. The CLI
   resolves the key exactly as the server does. At level 1 without a key
   the CLI signs with a random key of its own, so the server rejects what
   it generates (the CLI logs a warning): set ``FERNET_KEY``.

Personal API keys
********************

A personal API key is a long-lived bearer token (default 1 year,
``API_KEY_DURATION_DAYS``, at most 2 years at level 3) that authenticates the API as
an alternative to the short-lived session JWT — every endpoint accepts
either credential. It is meant for unattended automation.

- **Minted behind full authentication.** It is issued only on a full
  session; when the user has MFA enabled the server requires a fresh TOTP
  step-up (``API_KEY_STEPUP_TOTP``, on by default at level 3). It can be generated from
  the web client (Settings), the ``cornflow-client`` library
  (``create_api_key()`` after ``login``), or the CLI
  (``cornflow users api_key -u <username>``, trusted by machine access — no
  TOTP). Shown only once.
- **One active key per user.** Generating a new key supersedes the previous
  one; it is also revoked explicitly (``DELETE /user/api-key/`` or the
  Settings screen), and automatically on account lock and MFA reset, which also revoke a
  superseded key still in its rotation grace window. A
  routine password change does NOT revoke it (automation continuity).
  The key itself is never stored: revocation works because the key carries
  the user's api-key version, which is compared against the database on every
  request.
- **Rotation grace window.** After generating a new key the superseded one
  keeps working for ``API_KEY_ROTATION_GRACE_MINUTES`` (default 60, at most
  a day at level 3; 0 disables it), so a key wired into running automation can be
  replaced without a gap: **generate first, redeploy after**. Only the
  immediately superseded key benefits. An explicit revocation, an account
  lock and an MFA reset revoke both keys at once, with no grace.
- **Scope: full or read-only.** A key can be minted read-only (``"scope":
  "read"`` on the request, the *read-only* checkbox in the Settings screen,
  ``create_api_key(read_only=True)`` in the library, or ``--read-only`` in the
  CLI). A read-only key is refused on any request that is not a ``GET`` /
  ``HEAD`` / ``OPTIONS`` (403 with ``error_code: api_key_read_only``),
  whatever the user's own permissions are. This is the credential to hand to a
  reporting or BI consumer.
- **Expiry notifications.** ``cornflow tokens notify-expiry`` emails the key
  owner **and every platform administrator** when a key is close to expiring
  (``TOKEN_EXPIRY_NOTIFICATION_DAYS``, default ``30,7,3,2,1`` days; disable
  with ``TOKEN_EXPIRY_NOTIFICATIONS_ENABLED=0``). Run it **once a day** from
  cron or a Kubernetes CronJob — cornflow has no scheduler of its own::

      0 7 * * *  cornflow tokens notify-expiry

  The command is idempotent (running it repeatedly sends nothing extra) and
  recovers from missed runs: it warns as soon as a threshold has been crossed,
  and the email always states the real number of days left. It needs the SMTP
  settings (``SERVICE_EMAIL_*``); without them it logs a warning and still
  emits the ``apikey.expiry_notified`` audit event. Only keys generated after
  this version are covered (the issue timestamp did not exist before);
  regenerating a key starts the notifications for it.
- **Not for account management.** An API key can not reach the
  security-sensitive endpoints (password change, MFA, API key
  management, user/role administration): a leaked key can not escalate.
- **Disable per deployment** with ``PERSONAL_TOKEN_ENABLED=0``: the endpoint
  ``/user/api-key/`` answers 501 (and the web client hides the Settings
  section). This only stops the generation through the API: the keys
  already generated keep working until they expire or are revoked, and the
  CLI (``cornflow users api_key``) can still generate them.

Service users can hold an API key too. Because the cornflow↔airflow service
connection otherwise re-logs in with the service password on every task
(and the session token expires after 24 h at level 1 and 8 h at levels 2 and 3), the recommended setup is to
generate a key for the service user (``cornflow users api_key -u
service_user``) and expose it to Airflow as ``CORNFLOW_SERVICE_API_KEY``:
``connect_to_cornflow`` then uses the long-lived key and skips the per-task
login. Rotate it yearly (regenerate + update the variable).

Session management and inactivity timeout
********************************************

At level 3 (``REFRESH_TOKEN_ENABLED=1``, the default there) interactive
sessions use two tokens instead of one:

* an **access token**, short-lived (``ACCESS_TOKEN_DURATION_MINUTES``,
  default 15, at most 60 at level 3), sent as the Bearer credential on every request;
* a **refresh token**, bound to a session stored server-side (table
  ``session_tokens``), used *only* against ``POST /token/refresh/`` to obtain
  a new access + refresh token pair. It is rejected on every other endpoint.

At levels 1 and 2 the login returns a single session token valid for
``TOKEN_DURATION`` hours (24 at level 1, 8 at level 2), with no renewal:
once it expires it answers 401 and the user logs in again.
``REFRESH_TOKEN_ENABLED=1`` turns the renewable sessions on at those levels
too.

Each refresh **rotates** the refresh token and slides the **inactivity
window** (``REFRESH_TOKEN_INACTIVITY_MINUTES``, default 30, at most 720 at
level 3): a session with no refresh for longer than the window is closed
and requires a full re-login. Independently, no session outlives the
**absolute cap** (``REFRESH_TOKEN_ABSOLUTE_HOURS``, default 12, at most 24
at level 3). The web client
renews the access token transparently while the user is active, so the net
effect is a logout after ~30 minutes of inactivity and a re-login at least
every 12 hours.

Because sessions are stored server-side:

* ``POST /logout/`` revokes a single session (the web client calls it on
  logout);
* password change, account lockout and MFA reset revoke **all** the user's
  sessions (on top of the token-version bump);
* presenting an **already-rotated refresh token is treated as theft**: the
  whole session is revoked and a ``session.reuse_detected`` audit event is
  emitted.

``/token/refresh/`` and ``/logout/`` are rate-limited per IP with the login
limit, counting only their failed responses (see the per-IP rate limiting
above). Stale session rows are purged opportunistically at login;
``cornflow sessions purge`` deletes the rest (run it periodically, e.g. from
a cron job).

**Service users are exempt**: their login returns the single long-lived token
(``TOKEN_DURATION``) so the cornflow↔airflow connection is
unaffected — unattended automation should use a personal API key anyway. The
``cornflow-client`` library refreshes transparently too: on an expired access
token it renews the session and retries the call, and offers explicit
``refresh()`` / ``logout()`` methods. When the renewal is rejected because
the session has been closed, the library raises ``CornFlowApiError`` and
asks to log in again (see :ref:`Raising the security level`).

Renewable sessions are on by default at level 3;
``REFRESH_TOKEN_ENABLED=0`` restores the single-token behaviour there. Deployments upgrading to this
version must run the migration that creates the ``session_tokens`` table.

.. note::
   The web client keeps the refresh token in ``sessionStorage`` (per tab).
   Duplicating a browser tab copies it: the next refresh from one of the two
   tabs will be detected as a reuse of a rotated token and close the session
   in both. This strict behaviour is intentional (reuse detection protects
   against token theft); users should open a fresh tab and log in instead of
   duplicating one.

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
``mfa.reset``, ``apikey.issued`` / ``apikey.revoked``, ``bitoken.issued``,
``role.granted`` / ``role.revoked`` and the session events
``session.refreshed`` / ``session.logout`` / ``session.reuse_detected``.

The failed-login records may name the attempted (even non-existent) username:
this is intentional and useful to defenders because the audit channel is a
trusted internal sink. The client-facing responses stay generic and never
reveal whether a username or email exists.

This is the emission layer only. Collection, append-only retention, host time
synchronisation and alerting are the responsibility of the deployment's log
pipeline / SIEM (e.g. ship stdout to Loki / ELK / CloudWatch and alert on
repeated ``account.locked`` or ``apikey.issued`` bursts). Auditing can be
turned off with ``AUDIT_LOG_ENABLED=0`` (on at every level).

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
  base-uri 'none'`` — deny-by-default; the API returns JSON, so nothing
  needs to load. Override it with ``CONTENT_SECURITY_POLICY``. The
  interactive API docs get a policy of their own (see below), which
  ``CONTENT_SECURITY_POLICY`` does not change.
* ``Referrer-Policy: no-referrer`` — do not leak URLs (which may carry tokens,
  e.g. the password reset link) through the ``Referer`` header.
* ``Permissions-Policy`` — disables browser features the app does not use.
* ``Cache-Control: no-store`` — responses carry auth data and should not be
  cached (``SECURITY_NO_STORE=0`` to disable).
* The ``Server`` banner is overwritten and ``X-Powered-By`` removed to reduce
  version fingerprinting.

The whole set can be turned off with ``SECURITY_HEADERS_ENABLED=0``.

.. warning::
   **HSTS** (``Strict-Transport-Security``) is **on by default at level 3**,
   whatever ``FLASK_ENV`` is, and off at levels 1 and 2 (``HSTS_ENABLED``;
   ``max-age`` one year, ``includeSubDomains``). Only serve
   the header once TLS terminates in front of cornflow: a browser that has
   seen it will refuse plain HTTP afterwards. If TLS is not yet in place, set
   ``HSTS_ENABLED=0`` until it is. ``HSTS_PRELOAD`` is off by default (opting
   into the preload list is hard to reverse).

**CORS** is driven by ``CORS_ORIGINS``:

* default ``*`` (any origin) at levels 1 and 2,
* **at level 3 the default is empty — default-closed**: set ``CORS_ORIGINS`` to
  the web client origin(s), comma-separated (e.g.
  ``https://cornflow.example.com``), or the SPA will be unable to call the API
  from the browser.

Because authentication uses a Bearer token in the ``Authorization`` header
(not a cookie), classic CSRF is already mitigated; the CORS lock-down is
defense-in-depth and closes the previously wide-open ``*`` policy.

**Interactive API docs** (Swagger UI at ``/swagger-ui/`` and the OpenAPI
schema at ``/swagger/``) are **disabled by default at level 3**
(``CORNFLOW_DOCS_ENABLED=0``), whatever ``FLASK_ENV`` is, to shrink the
attack surface, and enabled at levels 1 and 2. With
``CORNFLOW_DOCS_ENABLED=1``, at any level, the Swagger UI loads and works in
the browser: its routes (the page, its static files and the schema) carry a
``Content-Security-Policy`` of their own::

    default-src 'none'; script-src 'self' 'sha256-<hash>'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'

It only lets the page load the scripts, the stylesheet and the icons served
by cornflow itself, the images embedded in the stylesheet (``data:``) and
requests to the same origin (the schema and *Try it out*). The inline script
that starts the page is allowed by its SHA-256 hash, computed on the page as
served, so it follows the URL under which cornflow is published. Inline
styles are allowed because the Swagger UI sets them to highlight examples
and responses; ``'unsafe-eval'`` and other origins are not allowed. The
Swagger UI is served from the static files bundled with flask-apispec, with
no external resources. The rest of the API keeps the strict policy above, or
``CONTENT_SECURITY_POLICY`` if it is set, which does not apply to the
Swagger UI routes. ``CORNFLOW_DOCS_ENABLED=0`` removes the page, its static
files and the schema (404).

Security levels
******************

``CORNFLOW_SECURITY_LEVEL`` selects one of three security levels. The level
sets the default value of every security setting described in this page.
Each setting can still be changed with its own environment variable, within
the limits of the level. The levels add up: level 2 includes level 1 and
level 3 includes level 2.

* **Level 1** (the default) behaves as cornflow 1.3.9 for sessions,
  passwords, CORS, Swagger, HSTS, BI tokens and user sign-up, so upgrading
  from 1.3.9 needs no change in deployments or clients. There are two
  visible changes: a token that is not valid answers 401 instead of 400 (see
  :ref:`Invalid tokens (401 and WWW-Authenticate)`), and BI tokens are
  issued with ``cornflow users bi_token -u <username>``, which replaces the
  command of 1.3.9 that asked for the password of a service user.
* **Level 2** adds the basic controls: password policy, one-time passwords,
  account lockout after 5 failed logins, a mandatory secret key of at least
  32 bytes, 8-hour sessions and user sign-up restricted to platform
  administrators.
* **Level 3** adds the rest: mandatory two-factor authentication, renewable
  sessions, password rotation every 120 days and BI tokens that expire after
  90 days. It also closes CORS, turns Swagger off and turns HSTS on.

The level applies whatever ``FLASK_ENV`` is: ``CORS_ORIGINS``,
``CORNFLOW_DOCS_ENABLED`` and ``HSTS_ENABLED`` no longer depend on it.

Choosing a security level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set ``CORNFLOW_SECURITY_LEVEL`` to ``1``, ``2`` or ``3`` (spaces around the
value are ignored). Without the variable cornflow uses level 1. Any other
value (another number, text or an empty value) stops cornflow from starting
with the message ``CORNFLOW_SECURITY_LEVEL must be 1, 2 or 3 (got '...')``:
``cornflow service init`` exits with code 1 before running the migrations,
creating users or starting gunicorn, and the other CLI commands fail with
the same message.

At startup cornflow logs the effective level, every variable that changes
a level default and every value adjusted to a limit, for example::

    Security level: 2
    Security level 2, changed setting: TOKEN_DURATION: level default 8.0, effective 12.0
    Security level 2, adjusted setting: LOGIN_MAX_ATTEMPTS: requested '20', applied 10 (maximum allowed at security level 2)

The log names each setting by its configuration key (``DOCS_ENABLED`` for
``CORNFLOW_DOCS_ENABLED``), never prints a secret key and hides the value of
``RATELIMIT_STORAGE_URI``. The level is not exposed through the API.

The ``docker-compose`` files of the repository carry
``CORNFLOW_SECURITY_LEVEL`` commented out, with value ``1``. The Helm chart
sets ``cornflow.env.CORNFLOW_SECURITY_LEVEL: "1"``; its ``values.yaml`` also
sets ``SIGNUP_ACTIVATED``, ``CORS_ORIGINS``, ``TOKEN_DURATION`` and
``PWD_ROTATION_TIME``, which override the level: at levels 2 and 3 set them
to ``null`` so that the level default applies (see the *Security level*
section of ``helm-charts/cornflow/README.md``).

Controls by security level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: Controls by security level
   :header-rows: 1
   :widths: 28 22 17 17 16

   * - Control
     - Variable
     - Level 1
     - Level 2
     - Level 3
   * - New database migrations applied at startup
     - —
     - yes
     - yes
     - yes
   * - bcrypt work factor
     - ``BCRYPT_LOG_ROUNDS``
     - 12
     - 12
     - 12
   * - Security audit log (``cornflow.audit``)
     - ``AUDIT_LOG_ENABLED``
     - 1
     - 1
     - 1
   * - HTTP security headers
     - ``SECURITY_HEADERS_ENABLED``
     - 1
     - 1
     - 1
   * - Error responses without internal details
     - —
     - yes
     - yes
     - yes
   * - Per-IP limit of login, token refresh and logout
     - ``RATELIMIT_LOGIN``
     - ``10 per minute``, failed responses only
     - same as level 1
     - same as level 1
   * - Per-IP limit of password recovery and reset
     - ``RATELIMIT_RECOVER``
     - ``5 per hour``, every request
     - same as level 1
     - same as level 1
   * - Platform roles, platform data isolation and attribution of service user
       updates
     - ``PLATFORM_DATA_ISOLATION``
     - 1
     - 1
     - 1
   * - Personal API keys
     - ``PERSONAL_TOKEN_ENABLED``
     - 1
     - 1
     - 1
   * - Personal API key of the service user for Airflow
     - ``CORNFLOW_SERVICE_API_KEY`` (Airflow side)
     - available
     - available
     - available
   * - Password recovery by link
     - ``CORNFLOW_UI_URL``
     - link if set; otherwise a temporary password
     - same as level 1
     - same as level 1
   * - Voluntary two-factor enrollment (``/mfa/setup/``, ``/mfa/verify/``)
     - ``MFA_ENABLED``
     - 0
     - 0
     - 1
   * - Mandatory two-factor authentication for internal users (except service
       users), with backup codes
     - ``MFA_REQUIRED``
     - 0
     - 0
     - 1
   * - Fresh TOTP code to generate a personal API key
     - ``API_KEY_STEPUP_TOTP``
     - 0
     - 0
     - 1
   * - Fresh TOTP code to grant a platform role
     - ``PLATFORM_ROLE_STEPUP_TOTP``
     - 0
     - 0
     - 1
   * - Sessions with refresh token
     - ``REFRESH_TOKEN_ENABLED``
     - 0
     - 0
     - 1
   * - Lifetime of the single session token (hours)
     - ``TOKEN_DURATION``
     - 24
     - 8
     - 8 (service users and fallback)
   * - Access token, inactivity window and session cap
     - ``ACCESS_TOKEN_DURATION_MINUTES``,
       ``REFRESH_TOKEN_INACTIVITY_MINUTES``, ``REFRESH_TOKEN_ABSOLUTE_HOURS``
     - not used
     - not used
     - 15 min, 30 min and 12 h
   * - Token that is not valid (expired, wrong signature or format, revoked)
     - —
     - 401 with ``WWW-Authenticate``
     - same as level 1
     - same as level 1
   * - Password rules
     - ``PWD_MIN_LENGTH``, ``PWD_MIN_ZXCVBN_SCORE``, ``PWD_HISTORY_SIZE``,
       ``PWD_MAX_SIMILARITY`` and rules without variable
     - those of 1.3.9: at least 5 characters, uppercase and lowercase letters,
       a number and a special character
     - at least 12 characters, uppercase and lowercase letters, a number and a
       special character; no spaces, no personal data, no 6 consecutive
       digits; zxcvbn score 3 or more; none of the last 10; not too similar to
       the current one (0.8)
     - same as level 2
   * - Password history
     - —
     - stored, not checked
     - stored and checked
     - same as level 2
   * - ``current_password`` to change your own password
     - —
     - not required (ignored)
     - required
     - required
   * - Passwords from the environment (admin, service and platform admin) when
       the user is created
     - —
     - rules of 1.3.9
     - password policy; cornflow does not start if they do not comply
     - same as level 2
   * - One-time passwords (sign-up by an administrator, password set by an
       administrator, temporary password of the recovery)
     - —
     - no
     - yes
     - yes
   * - Forced-change flags set by the migration ``b7a1c9d807e5``
     - —
     - ignored
     - applied
     - applied
   * - ``change_password`` in the login response
     - —
     - password older than ``PWD_ROTATION_TIME`` days (as in 1.3.9)
     - forced-change flag or age
     - same as level 2
   * - Password rotation (an expired password can only be changed)
     - ``PWD_ROTATION_ENFORCE`` / ``PWD_ROTATION_TIME``
     - 0 / 120 (warning only)
     - 0 / 120 (warning only)
     - 1 / 120
   * - Account lockout after consecutive failed logins (service users exempt)
     - ``LOGIN_MAX_ATTEMPTS``
     - 0: no lockout, failures not counted
     - 5
     - 5
   * - Automatic unlock
     - —
     - —
     - no
     - no
   * - Who unlocks an account through the API
     - —
     - as level 2, if the lockout is turned on
     - platform admin; client admin only users without a platform role
     - platform admin only
   * - What a lock revokes
     - —
     - sessions and API keys, if the lockout is turned on
     - sessions and API keys
     - same as level 2
   * - User sign-up (``/signup/``)
     - ``SIGNUP_ACTIVATED``
     - 2: administrators
     - 3: platform administrators only
     - 3
   * - Management of roles, permissions, actions and API views
     - —
     - admin and platform admin (the platform roles stay with the platform
       admin)
     - platform admin only
     - platform admin only
   * - Revoking the admin role from another admin
     - —
     - admin and platform admin
     - platform admin only
     - platform admin only
   * - BI tokens
     - ``BI_TOKEN_DURATION_DAYS``
     - 0: no expiration
     - 0: no expiration
     - 90 days; tokens without expiration date are rejected
   * - Effective secret key (``FERNET_KEY``, else ``SECRET_KEY``)
     - —
     - missing: random key with a warning; shorter than 32 bytes: warning
     - required, at least 32 bytes
     - same as level 2
   * - ``SECRET_BI_KEY``
     - —
     - missing or shorter than 32 bytes: warning
     - missing: warning; if set, at least 32 bytes
     - same as level 2
   * - CORS
     - ``CORS_ORIGINS``
     - ``*``
     - ``*``
     - empty (closed): set ``CORS_ORIGINS``.
   * - Swagger UI and OpenAPI schema
     - ``CORNFLOW_DOCS_ENABLED``
     - 1
     - 1
     - 0
   * - HSTS
     - ``HSTS_ENABLED``
     - 0
     - 0
     - 1

The CLI (``cornflow users unlock``, ``cornflow users create``) works at
every level: shell access to the server is already privileged. The meaning
of ``SIGNUP_ACTIVATED`` is: ``0`` sign-up disabled, ``1`` open sign-up
without authentication (new users get ``DEFAULT_ROLE``), ``2`` only
administrators, ``3`` only platform administrators. ``cornflow service
init`` no longer sets it, so the level default applies.

Default value of each setting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every security setting has a default value at each level and can be
changed with its own variable, within the limits of the level (see
:ref:`Limits by security level`). These settings change their default with
the level:

.. list-table:: Settings whose default depends on the level
   :header-rows: 1
   :widths: 40 20 20 20

   * - Variable
     - Level 1
     - Level 2
     - Level 3
   * - ``MFA_ENABLED``
     - 0
     - 0
     - 1
   * - ``MFA_REQUIRED``
     - 0
     - 0
     - 1
   * - ``API_KEY_STEPUP_TOTP``
     - 0
     - 0
     - 1
   * - ``PLATFORM_ROLE_STEPUP_TOTP``
     - 0
     - 0
     - 1
   * - ``REFRESH_TOKEN_ENABLED``
     - 0
     - 0
     - 1
   * - ``TOKEN_DURATION`` (hours)
     - 24
     - 8
     - 8
   * - ``PWD_MIN_LENGTH``
     - 5
     - 12
     - 12
   * - ``PWD_MIN_ZXCVBN_SCORE``
     - 0 (not checked)
     - 3
     - 3
   * - ``PWD_ROTATION_ENFORCE``
     - 0
     - 0
     - 1
   * - ``LOGIN_MAX_ATTEMPTS``
     - 0 (no lockout)
     - 5
     - 5
   * - ``SIGNUP_ACTIVATED``
     - 2
     - 3
     - 3
   * - ``BI_TOKEN_DURATION_DAYS``
     - 0 (no expiration)
     - 0 (no expiration)
     - 90
   * - ``CORS_ORIGINS``
     - ``*``
     - ``*``
     - empty (closed)
   * - ``CORNFLOW_DOCS_ENABLED``
     - 1
     - 1
     - 0
   * - ``HSTS_ENABLED``
     - 0
     - 0
     - 1

These settings have the same default at every level:

.. list-table:: Settings with the same default at every level
   :header-rows: 1
   :widths: 40 25 35

   * - Variable
     - Default
     - Notes
   * - ``BCRYPT_LOG_ROUNDS``
     - 12
     - at least 12 at every level
   * - ``AUDIT_LOG_ENABLED``
     - 1
     -
   * - ``SECURITY_HEADERS_ENABLED``
     - 1
     -
   * - ``RATELIMIT_ENABLED``
     - 1
     -
   * - ``RATELIMIT_LOGIN``
     - ``10 per minute``
     - only failed responses count
   * - ``RATELIMIT_RECOVER``
     - ``5 per hour``
     - every request counts
   * - ``RATELIMIT_TRUST_FORWARDED_FOR``
     - 0
     - set 1 only behind a trusted reverse proxy
   * - ``PLATFORM_DATA_ISOLATION``
     - 1
     -
   * - ``PERSONAL_TOKEN_ENABLED``
     - 1
     -
   * - ``CORNFLOW_UI_URL``
     - unset
     -
   * - ``ACCESS_TOKEN_DURATION_MINUTES``
     - 15
     - used with ``REFRESH_TOKEN_ENABLED=1``
   * - ``REFRESH_TOKEN_INACTIVITY_MINUTES``
     - 30
     - used with ``REFRESH_TOKEN_ENABLED=1``
   * - ``REFRESH_TOKEN_ABSOLUTE_HOURS``
     - 12
     - used with ``REFRESH_TOKEN_ENABLED=1``
   * - ``PWD_HISTORY_SIZE``
     - 10
     - stored at every level, checked from level 2
   * - ``PWD_MAX_SIMILARITY``
     - 0.8
     - checked from level 2
   * - ``PWD_ROTATION_TIME`` (days)
     - 120
     -
   * - ``API_KEY_DURATION_DAYS``
     - 365
     -
   * - ``API_KEY_ROTATION_GRACE_MINUTES``
     - 60
     -
   * - ``MFA_SETUP_TOKEN_DURATION_MINUTES``
     - 10
     -
   * - ``PWD_RESET_TOKEN_DURATION_MINUTES``
     - 30
     -
   * - ``MFA_BACKUP_CODES_NUMBER``
     - 8
     -
   * - ``CONTENT_SECURITY_POLICY``
     - unset (``default-src 'none'; frame-ancestors 'none'; base-uri 'none'``)
     -
   * - ``PERMISSIONS_POLICY``
     - unset (strict built-in policy)
     -
   * - ``REFERRER_POLICY``
     - unset (``no-referrer``)
     -
   * - ``SECURITY_NO_STORE``
     - 1
     -
   * - ``HSTS_MAX_AGE``
     - 31536000
     -
   * - ``HSTS_INCLUDE_SUBDOMAINS``
     - 1
     -
   * - ``HSTS_PRELOAD``
     - 0
     -
   * - ``RATELIMIT_STORAGE_URI``
     - ``memory://``
     - use a shared backend with several workers
   * - ``SERVICE_USER_ALLOW_PASSWORD_LOGIN``
     - 1
     -
   * - ``TOKEN_EXPIRY_NOTIFICATIONS_ENABLED``
     - 1
     -
   * - ``TOKEN_EXPIRY_NOTIFICATION_DAYS``
     - ``30,7,3,2,1``
     -

Limits by security level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Level 1 only keeps the bcrypt minimum: every other numeric setting can take
any value (``TOKEN_DURATION`` can go above 24 hours, as in 1.3.9, and
``LOGIN_MAX_ATTEMPTS=0`` turns the lockout off). Level 2 adds limits to the
controls it introduces and level 3 adds the limits of the remaining
settings. Switches (``MFA_ENABLED``, ``REFRESH_TOKEN_ENABLED``,
``CORS_ORIGINS``, ``HSTS_ENABLED``...) have no limits at any level.

.. list-table:: Limits of each setting
   :header-rows: 1
   :widths: 40 20 20 20

   * - Variable
     - Level 1
     - Level 2
     - Level 3
   * - ``BCRYPT_LOG_ROUNDS``
     - 12 or more
     - 12 or more
     - 12 or more
   * - ``TOKEN_DURATION``
     - —
     - 24 or less
     - 24 or less
   * - ``PWD_MIN_LENGTH``
     - —
     - 12 or more
     - 12 or more
   * - ``PWD_MIN_ZXCVBN_SCORE``
     - —
     - 3 or more
     - 3 or more
   * - ``PWD_HISTORY_SIZE``
     - —
     - 10 or more
     - 10 or more
   * - ``PWD_MAX_SIMILARITY``
     - —
     - 0.9 or less
     - 0.9 or less
   * - ``LOGIN_MAX_ATTEMPTS``
     - —
     - 1 to 10
     - 1 to 10
   * - ``ACCESS_TOKEN_DURATION_MINUTES``
     - —
     - —
     - 60 or less
   * - ``REFRESH_TOKEN_INACTIVITY_MINUTES``
     - —
     - —
     - 720 or less
   * - ``REFRESH_TOKEN_ABSOLUTE_HOURS``
     - —
     - —
     - 24 or less
   * - ``PWD_ROTATION_TIME``
     - —
     - —
     - 365 or less
   * - ``BI_TOKEN_DURATION_DAYS``
     - —
     - —
     - 1 to 365
   * - ``API_KEY_DURATION_DAYS``
     - —
     - —
     - 730 or less
   * - ``API_KEY_ROTATION_GRACE_MINUTES``
     - —
     - —
     - 1440 or less
   * - ``MFA_SETUP_TOKEN_DURATION_MINUTES``
     - —
     - —
     - 30 or less
   * - ``PWD_RESET_TOKEN_DURATION_MINUTES``
     - —
     - —
     - 60 or less
   * - ``MFA_BACKUP_CODES_NUMBER``
     - —
     - —
     - 20 or less
   * - Effective secret key
     - — (warning below 32 bytes)
     - 32 bytes or more
     - 32 bytes or more
   * - ``SECRET_BI_KEY``
     - — (warning below 32 bytes)
     - 32 bytes or more, if set
     - 32 bytes or more, if set

A value outside the limits of the level is handled as follows:

* A 0, or a negative value, that turns off a control the level requires
  stops cornflow from starting: ``LOGIN_MAX_ATTEMPTS`` at levels 2 and 3
  and ``BI_TOKEN_DURATION_DAYS`` at level 3. The message names the
  variable, the value, the allowed range and the level default, for
  example: ``LOGIN_MAX_ATTEMPTS=0 turns off account lockout, which security
  level 2 does not allow: set a value between 1 and 10, or leave it unset
  to use the level default (5)``.
* Any other value outside the limits is replaced by the limit, with a
  warning in the log (``adjusted setting``): for example,
  ``LOGIN_MAX_ATTEMPTS=20`` at level 2 becomes 10 and
  ``BI_TOKEN_DURATION_DAYS=500`` at level 3 becomes 365.
* A value that is not a number is replaced by the level default, also with
  a warning. An empty numeric variable counts as unset. Text settings
  (``CORS_ORIGINS``, ``RATELIMIT_LOGIN``...) are used verbatim, so
  ``CORS_ORIGINS=""`` closes CORS.

Secret key (FERNET_KEY)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

cornflow signs the session tokens, the personal API keys and the temporary
tokens (two-factor enrollment, password reset) with one secret key, and
derives from it the key that encrypts the TOTP secrets stored in the
database. The key comes from:

#. ``FERNET_KEY``;
#. if it is not set, ``SECRET_KEY``, kept as a fallback;
#. if neither is set, a random key generated at startup, only at level 1.

A variable that is set but empty (or only contains spaces) counts as unset.
When ``FERNET_KEY`` and ``SECRET_KEY`` are both set with different values,
cornflow uses ``FERNET_KEY``, ignores ``SECRET_KEY`` and logs a warning.
The key is resolved in the configuration, so the server and the CLI run
with ``docker exec`` (``cornflow users api_key``, ``bi_token``)
sign with the same key as long as the variables are set in the container
environment. No message ever prints the value of a key.

The key must have at least 32 bytes (256 bits, as required by RFC 7518 for
HMAC-SHA256). ``FERNET_KEY`` is the recommended variable; ``SECRET_KEY`` is
only an alternative, read when ``FERNET_KEY`` is not set. Generate the key
with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

The command prints a Fernet key: 44 URL-safe base64 characters that encode
32 random bytes, so it meets the minimum of 32 bytes. A key generated this
way is also valid for Airflow, which requires a valid Fernet key
(``AIRFLOW__CORE__FERNET_KEY``): deployment tools that pass the same
``FERNET_KEY`` to cornflow and to Airflow can use a single key. The command
needs the ``cryptography`` package, a dependency of cornflow, so it works
inside the cornflow image or in any environment where cornflow is
installed.

* **Level 1**: without a key cornflow starts with a random key and logs a
  warning. ``cornflow service init`` generates it once per start, before
  launching gunicorn, and passes it to every worker in the internal
  variable ``CORNFLOW_EPHEMERAL_SECRET_KEY`` (do not set it yourself). Every
  restart invalidates all sessions and API keys, the API keys generated
  with the CLI are not accepted by the server, and, if ``MFA_ENABLED=1``,
  the users who enroll in two-factor authentication can not log in after a
  restart (the login answers 500) until an administrator resets their MFA
  with ``DELETE /user/<id>/mfa/``, which also revokes their sessions and API
  keys. A key shorter than 32 bytes only logs a warning.
* **Levels 2 and 3**: the key is mandatory and must have at least 32 bytes.
  Otherwise cornflow does not start, with a message such as ``Security
  level 2 requires a secret key: set FERNET_KEY (or SECRET_KEY) to a value
  of at least 32 bytes (256 bits)``.

``SECRET_BI_KEY`` signs the BI tokens. At level 1 a missing or short value
only logs a warning. At levels 2 and 3 a missing value logs a warning (BI
tokens can not be issued) and a value shorter than 32 bytes stops cornflow
from starting.

Changing the effective key invalidates every session, every personal API
key (including the one in ``CORNFLOW_SERVICE_API_KEY``), the pending
password reset links and the stored TOTP secrets: users with two-factor
authentication can not log in until an administrator resets their MFA.
Changing ``SECRET_BI_KEY`` invalidates every BI token.

When upgrading:

* Deployments that already set ``FERNET_KEY`` keep their key.
* A deployment that sets both variables with different values and was
  signing with ``SECRET_KEY`` (for example, started with ``flask`` instead
  of ``cornflow service init``) now signs with ``FERNET_KEY``, which closes
  the existing sessions and invalidates its API keys and MFA enrollments.
  Give both variables the same value to keep them.
* ``cornflow service init`` no longer writes ``SECRET_KEY`` in the
  environment. External applications whose configuration inherits from the
  cornflow configuration get the same key; those that read ``SECRET_KEY``
  on their own must have it set in their environment.

In Docker and Kubernetes:

* The ``docker-compose`` files of the repository set a fixed ``FERNET_KEY``
  and ``SECRET_BI_KEY`` for **development only**. Any other deployment must
  set its own values.
* The Helm chart generates ``FERNET_KEY`` and ``SECRET_BI_KEY`` in the
  Secret ``<release>-cornflow-keys`` when it is installed and keeps them
  across upgrades. It can use an existing Secret instead
  (``cornflow.keys.existingSecret``), which is required with
  ``helm template`` and with GitOps tools that render the chart without a
  cluster. See the *Secret keys* section of the chart README
  (`helm-charts/cornflow/README.md
  <https://github.com/baobabsoluciones/cornflow/blob/master/helm-charts/cornflow/README.md>`_).

Two-factor enrollment (MFA_ENABLED)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``MFA_ENABLED`` (``0`` or ``1``) controls whether users can enroll in
two-factor authentication: 0 at levels 1 and 2, 1 at level 3. With
``MFA_ENABLED=0``:

* ``POST /mfa/setup/`` and ``POST /mfa/verify/`` stay registered but answer
  501 with ``{"error": "Two-factor authentication enrollment is disabled on
  this deployment"}``. The check runs after authentication: a request
  without a token still answers 400 and one with a token that is not valid,
  401.
* Users who already enrolled keep using their second factor: the login
  still asks for the code.
* The MFA reset (``DELETE /user/<id>/mfa/``) stays available, so an
  administrator can remove the second factor of a user.

``MFA_REQUIRED``, ``API_KEY_STEPUP_TOTP`` and ``PLATFORM_ROLE_STEPUP_TOTP``
set to 1 need ``MFA_ENABLED=1``. cornflow checks it at startup with the
effective values (the level defaults plus the variables that are set) and
does not start otherwise, naming the variables to change, for example:
``MFA_REQUIRED=1 needs MFA_ENABLED=1, but MFA_ENABLED is 0: set
MFA_ENABLED=1, or set MFA_REQUIRED to 0``. The defaults of the three levels
always pass the check. The fresh TOTP codes of ``API_KEY_STEPUP_TOTP`` and
``PLATFORM_ROLE_STEPUP_TOTP`` are only asked to users who have enrolled.

``MFA_ENABLED`` is not exposed through the API: a web client that offers
the enrollment on a deployment with ``MFA_ENABLED=0`` gets the 501.

Invalid tokens (401 and WWW-Authenticate)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At every level, a request with a token that is not valid answers 401 with
the header ``WWW-Authenticate: Bearer error="invalid_token",
error_description="<message>"`` and the body ``{"error": "<message>"}``.
This covers:

* an expired token, also from OpenID Connect;
* a token with a wrong signature or format, also from OpenID Connect;
* a revoked token: closed or expired session, old token version (after a
  password change, an account lock or an MFA reset) or revoked API key;
* the token of a user that no longer exists;
* a refresh token used on any endpoint other than ``/token/refresh/``, or a
  refresh token that is not valid on ``/token/refresh/``;
* an expired or invalid BI token and, at level 3, a BI token without
  expiration date.

**This is a visible change from cornflow 1.3.9**, where an expired token, a
token with a wrong signature or format, the token of a deleted user and an
expired or invalid BI token answered 400. ``cornflow-client`` 1.4 accepts
both codes; other clients that relied on the 400 must handle the 401. The
header is informative: clients do not need it, but can read the reason in
``error_description``.

These requests keep answering 400, without the header, because they carry
no token to assess: no ``Authorization`` header, a header that does not
follow ``Bearer <token>`` (or an empty token) and ``/token/refresh/``
without ``refresh_token``. A login with a wrong username or password also
answers 400. ``GET /token/`` keeps answering 200 with ``valid: 0`` and
``POST /logout/`` keeps answering 200.

Raising the security level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moving a running deployment to a higher level changes things for its users
and clients.

From level 1 to level 2:

* Set ``FERNET_KEY`` (at least 32 bytes) and, if you use BI tokens,
  ``SECRET_BI_KEY`` (at least 32 bytes): cornflow does not start without
  the first one. A deployment that was running with a random key loses its
  sessions and API keys once.
* Set ``CORNFLOW_ADMIN_PWD``, ``CORNFLOW_SERVICE_PWD`` and
  ``CORNFLOW_PLATFORM_ADMIN_PWD`` to values that comply with the password
  policy if those users have not been created yet; otherwise cornflow does
  not start. Existing users are not checked.
* Every user flagged by the migration ``b7a1c9d807e5`` (all the users that
  had a password when it ran) or created with ``cornflow users create ...
  --force-password-change`` must change the password at the next login:
  until then every other endpoint answers 403 with ``error_code:
  password_rotation``. ``GET /user/`` returns the flag as stored, also at
  level 1, so administrators can see in advance who will be affected.
* New passwords must follow the password policy, users must send
  ``current_password`` to change their own password (the web client of
  1.3.9 does not send it) and the passwords set by an administrator
  (also at sign-up) or by the password recovery are one-time.
* Only platform administrators create users through ``/signup/``: client
  administrators no longer can. Provision a platform administrator
  (``CORNFLOW_PLATFORM_ADMIN_USER`` and ``CORNFLOW_PLATFORM_ADMIN_PWD``, or
  ``cornflow users create platform_admin``) or create the users with the
  CLI (``cornflow users create``).
* Client administrators lose the management of roles, permissions, actions
  and API views, and can no longer revoke the admin role from another
  admin: the base permissions of the level are registered again at every
  start.
* Accounts are locked after 5 consecutive failed logins. A lock revokes the
  sessions and the personal API keys of the user, including the keys of
  their unattended processes. Client administrators can unlock users
  without a platform role, platform administrators can unlock anyone, and
  so can ``cornflow users unlock``.
* Sessions last 8 hours instead of 24.

From level 2 to level 3:

* Every internal user except service users must enroll in two-factor
  authentication at the next login (``MFA_ENABLED`` and ``MFA_REQUIRED``
  become 1). Generating a personal API key or granting a platform role
  asks for a fresh TOTP code.
* Users whose password is older than 120 days (``PWD_ROTATION_TIME``) must
  change it at the next login.
* BI tokens without expiration date (issued at levels 1 and 2, or by
  1.3.9) stop working: they answer 401 with ``The BI token has no
  expiration date and is no longer accepted, please regenerate the BI
  token``. Regenerate them with ``cornflow users bi_token -u <username>``;
  the new ones expire after 90 days. A token issued at a lower level with
  an expiration date further than 365 days away keeps working until it
  expires.
* Interactive sessions use an access token of 15 minutes renewed with a
  refresh token; a session is closed after 30 minutes without activity and
  after 12 hours at most. Clients must renew the token. ``cornflow-client``
  1.4 renews it transparently and, when the session has been closed, raises
  ``CornFlowApiError`` with the message ``The session has been closed
  (inactivity or maximum session length). Log in again; for unattended
  processes use a personal API key (set_api_key, or
  CORNFLOW_SERVICE_API_KEY in Airflow).`` The same message appears when the
  session has been revoked (logout from another place, account lock,
  password change). Unattended processes should use a personal API key.
  Service users keep a single token of ``TOKEN_DURATION`` hours.
* Client administrators can no longer unlock accounts: only platform
  administrators, or the CLI.
* CORS is closed (set ``CORS_ORIGINS`` to the origin of the web client),
  Swagger is off and HSTS is on (serve cornflow behind TLS).
* The limits of level 3 apply: values above them are replaced by the limit.

Going down a level keeps the data: the forced-change flags stay in the
database (level 1 ignores them), locked accounts stay locked until someone
unlocks them and enrolled users keep their second factor.

Server UAT battery by level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The server UAT battery (``cornflow/tests/unit/test_uat_hardening_*.py``)
checks the behaviour of one security level, selected with
``CORNFLOW_SECURITY_LEVEL`` (level 1 when it is not set, so the full unit
test suite runs it at level 1). Run it at each level from
``cornflow-server/``, with the environment variables of the unit tests (as
in the CI workflow ``test_cornflow_server.yml``)::

    CORNFLOW_SECURITY_LEVEL=1 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"
    CORNFLOW_SECURITY_LEVEL=2 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"
    CORNFLOW_SECURITY_LEVEL=3 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"

A case that does not apply to the level is skipped with a reason that says
so, and the cases that can only be checked in the web client are skipped
too. Any other value of ``CORNFLOW_SECURITY_LEVEL`` makes the battery fail
to load.

Roles definition
*********************

In cornflow there is a differentiation between user roles with different characteristics::

    Platform admin - platform operator: superset of the client admin. It is the only role that can grant or revoke the platform roles and unlock any account; at levels 2 and 3 it is also the only one that can create users, manage roles and permissions (roles, permission, apiview and action endpoints) and revoke the admin role from a user
    Platform planner - internal (platform operator) user with the same permissions as a client planner
    Platform viewer - internal (platform operator) user with the same permissions as a client viewer
    Admin - client administrator: manages the users of their own deployment (disable users, assign roles, manage DAG access). At level 1 it also creates users, manages roles and permissions and revokes the admin role, as in 1.3.9; at levels 1 and 2 it unlocks users without a platform role. It can never grant or revoke platform roles
    Service - service user role reserved for service accounts (cornflow and airflow communication)
    Viewer - read only user
    Planner - the general user of cornflow can create jobs and send models to solve

The split between platform admin and client admin depends on the security
level. At levels 2 and 3 the roles, permissions, apiview and action
endpoints require the platform_admin role, and so do revoking the admin
role from a user and creating users (``SIGNUP_ACTIVATED=3``); at level 3,
unlocking accounts too. At level 1 the client admin keeps what it had in
1.3.9: it manages roles, permissions, actions and API views, assigns and
revokes roles (also the admin role) and creates users, but it can not
grant or revoke platform roles, create or change roles with ids 900-999,
nor change the permissions of the platform roles (403). At levels 1 and 2
the client admin unlocks the accounts of users without a platform role.
The base permissions of the level are registered at every start
(``cornflow service init`` runs ``access_init``), which also deletes the
permissions that do not belong to the base set, including those created by
hand through the API. The platform admin inherits every client-admin
permission on top of the platform-only ones.

The **platform viewer** and **platform planner** roles exist to tell internal
(platform operator) users apart from external (client) ones: they carry
exactly the permissions of their client counterpart — each platform role
inherits every view its client equivalent can access — and only differ in
what they *are*, not in what they can do. **Granting or revoking any platform
role requires the platform administrator**: a client admin can neither
escalate a user (or themselves) into the platform side nor strip a platform
role. Create these users with ``cornflow users create platform_viewer`` /
``platform_planner`` or assign the role from the roles-management screen (the
platform roles are only offered to platform administrators).

**Data isolation.** The instances, executions and cases created by a platform
user are **invisible to client users** — including client admins, who
otherwise see every object of the deployment. This keeps the test data an
operator produces out of sight on shared or staging environments. The reverse
is not restricted: platform users are the operators and keep the visibility
their role grants them (so a platform *planner*, being a regular non-admin
user, still only sees its own objects, while a platform *admin* sees
everything). Disable with ``PLATFORM_DATA_ISOLATION=0``.

**Role ids.** Roles are identified by integer ids, allocated as follows::

    0-4         core client roles (dummy, viewer, planner, admin, service)
    5-899       free for the custom roles of external applications
    900-999     reserved for the cornflow platform roles
    1000-       free as well

Each platform role is its client counterpart **+ 900** (viewer ``1`` ->
platform viewer ``901``, planner ``2`` -> platform planner ``902``, admin
``3`` -> platform admin ``903``). Role registration **stops cornflow from starting** if a
custom role declares an id inside the reserved range, or if a role already
stored in the database occupies a platform-role id under a different name. That turns what would be a silent
reassignment of existing role assignments into an explicit error naming the
offending role.

``POST /roles/`` accepts an optional ``id``. Without it the new role gets
the next free id below 900. An id in 900-999 answers 403 to a client admin
and 400 to a platform admin (such a role would stop cornflow from
starting).

.. note::
   A service account acts on behalf of a user, so an update it performs never
   changes the owner of the affected object: when airflow writes back a
   solution, checks or KPIs, the execution/instance keeps its original
   ``user_id`` and stays visible to the user who created it.

.. warning::
   At levels 2 and 3 a deployment needs at least one platform administrator
   to create users and manage roles (and, at level 3, to unlock accounts).
   Provision one with
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
    CORNFLOW_SERVICE_PWD - service user account password (default value ``Service_user1234``, the same as in 1.3.9)

This connection is provided by::

    AIRFLOW_CONN_CF_URI="cornflow://CORNFLOW_SERVICE_USER:CORNFLOW_SERVICE_PWD@cornflowserveraddress:cornflowserverport"

Keep in mind to change default credentials when going to production.

Manage cornflow users
***********************

In the cornflow image, if no environment variables are set, an admin user is created with these credentials::

    CORNFLOW_ADMIN_USER - cornflow_admin
    CORNFLOW_ADMIN_EMAIL - cornflow_admin@cornflow.com
    CORNFLOW_ADMIN_PWD - Cornflow_admin1234

These defaults are those of 1.3.9 and only comply with the password rules
of level 1: at levels 2 and 3 set your own values, or cornflow does not
start. The ``docker-compose`` files and the Helm chart set explicit values
that comply with the policy.

It is advisable to change the default admin user and keep the password in a safe place.

To create a user, you must interact with the cornflow application through an `endpoint of its API <https://baobabsoluciones.github.io/cornflow/dev/endpoints.html#module-cornflow.endpoints.user>`_. Check the API docs for the users `here <https://baobabsoluciones.github.io/corn/stable-rest-api-ref.html#tag/Users>`_. Who can create users through ``/signup/`` depends on ``SIGNUP_ACTIVATED``: administrators at level 1 (2) and only platform administrators at levels 2 and 3 (3). The CLI (``cornflow users create``) can create users at every level.

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
