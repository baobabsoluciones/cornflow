"""
Shared support for the server UAT battery of the security hardening
(``cornflow/tests/unit/test_uat_hardening_*.py``).

Each test is named after the id of its case in the UAT sheet
(``test_uat_6_5_...`` covers case 6.5) and checks what that case means at the
security level selected with ``CORNFLOW_SECURITY_LEVEL``: 1, 2 or 3, and level
1 when the variable is unset, as in cornflow itself. Any other value stops the
battery before it runs.

Every case runs with the default values of its level
(``cornflow.shared.security_levels``) plus a few settings of the test suite:
rate limiting off except in the cases that check it, a low bcrypt work factor
and fixed keys. A case that changes a setting on purpose (for example
``LOGIN_MAX_ATTEMPTS=3`` to check the account lockout at level 1, where it is
off by default) does it through the same resolution as the environment, so the
limits of the level still apply.

A case that does not apply at a level is skipped with a reason that names the
level (for example the token renewal cases at levels 1 and 2). The cases that
can only be checked in the web client are skipped at every level with
:func:`ui_only` and belong to the cornflow-ui battery.

Run the battery at each level from ``cornflow-server/``, with the environment
of the unit tests (``FLASK_ENV=testing``, ``DATABASE_URL``...)::

    CORNFLOW_SECURITY_LEVEL=1 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"
    CORNFLOW_SECURITY_LEVEL=2 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"
    CORNFLOW_SECURITY_LEVEL=3 python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"

The whole unit test suite runs the battery at level 1.

The cases the kit could not run are covered too: e-mail with the SMTP client
replaced by an in-process fake (:class:`FakeSMTP`), TLS through the
``X-Forwarded-Proto`` header and session windows with a simulated clock
(``freezegun``).
"""

import json
import os
import sys
import unittest
from types import MappingProxyType
from unittest.mock import patch

import jwt
import pyotp
from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import (
    INVALID_TOKEN_ERROR_CODE,
    WWW_AUTHENTICATE_HEADER,
)
from cornflow.shared.security_levels import (
    SECURITY_LEVEL_ENV_VAR,
    default_values,
    parse_security_level,
)
from cornflow.tests.const import LOGIN_URL, PREFIX
from cornflow.tests.security_levels_support import security_level_config

MFA_SETUP_URL = PREFIX + "/mfa/setup/"
MFA_VERIFY_URL = PREFIX + "/mfa/verify/"

def read_security_level(environ=None) -> int:
    """Level of the battery: CORNFLOW_SECURITY_LEVEL, 1 when unset. ValueError otherwise."""
    environ = os.environ if environ is None else environ
    level, error = parse_security_level(environ.get(SECURITY_LEVEL_ENV_VAR))
    if error:
        raise ValueError(
            f"{error}: the UAT battery runs at security level 1, 2 or 3 "
            f"(leave {SECURITY_LEVEL_ENV_VAR} unset for level 1)"
        )
    return level


LEVEL = read_security_level()
LEVEL_DEFAULTS = MappingProxyType(default_values(LEVEL))
sys.stderr.write(f"UAT hardening battery: security level {LEVEL}\n")


JSON_HEADER = {"Content-Type": "application/json"}

# Passwords that comply with the policy, one per user of the battery
PASSWORDS = {
    "cfadmin": "Kd8-rVt.Nq2Wp5",
    "service_user": "Xq7-mBv.Ld9Rn2",
    "cfplatform": "Zc4-hJm.Bt6Vx9",
}
DEFAULT_PASSWORD = "Gv5-pLx.Wr8Tm3"


def level() -> int:
    return LEVEL


def at_least(minimum: int) -> bool:
    return LEVEL >= minimum


def by_level(level1, level2, level3):
    """Value that applies at the battery level (expected values of table 4.2)."""
    return (level1, level2, level3)[LEVEL - 1]


def level_overrides(level1=None, level2=None, level3=None) -> dict:
    """Settings a case changes on purpose at some levels (precedence over the level)."""
    return dict((level1, level2, level3)[LEVEL - 1] or {})


def only_at_levels(*levels, reason: str):
    """Skips the test at the other levels with a reason that names the level."""
    return unittest.skipUnless(LEVEL in levels, f"security level {LEVEL}: {reason}")


NO_RENEWAL_REASON = (
    "no token renewal at security levels 1 and 2 (REFRESH_TOKEN_ENABLED=0)"
)
requires_token_renewal = only_at_levels(3, reason=NO_RENEWAL_REASON)

# Settings changed on purpose by some cases (they go through the same
# resolution as the environment, see security_levels_support)
MFA_ENROLLMENT_OVERRIDES = level_overrides(
    level1={"MFA_ENABLED": 1}, level2={"MFA_ENABLED": 1}
)
LOCKOUT_OVERRIDES = level_overrides(level1={"LOGIN_MAX_ATTEMPTS": 3})
ROTATION_OVERRIDES = level_overrides(level1={"PWD_ROTATION_ENFORCE": 1})

# Who can sign up users at the level: SIGNUP_ACTIVATED is 2 at level 1 (any
# admin) and 3 at levels 2 and 3 (platform administrators only)
SIGNUP_ADMIN = "cfadmin" if LEVEL == 1 else "cfplatform"


def ui_only(reason: str):
    """
    Marks a case that can only be checked in the web client. It keeps its
    test (with the case id) but is skipped: it belongs to cornflow-ui.
    """
    return unittest.skip(f"cornflow-ui: {reason}")


def auth_header(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def uat_env_name(key_environ=None, **overrides) -> str:
    """Name of the configuration of the battery level plus the overrides, for create_app."""
    return security_level_config(LEVEL, key_environ=key_environ, **overrides)


class FakeSMTP:
    """
    In-process replacement of ``smtplib.SMTP_SSL`` that records the messages
    instead of sending them. Use it with :meth:`UatTestCase.fake_smtp`.
    """

    sent = []

    def __init__(self, server, port, *args, **kwargs):
        self.server = server
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, user, password):
        return 235, b"ok"

    def sendmail(self, sender, receivers, message):
        if isinstance(receivers, str):
            receivers = [receivers]
        FakeSMTP.sent.append(
            {"from": sender, "to": list(receivers), "message": message}
        )
        return {}

    def quit(self):
        return None


class UatTestCase(TestCase):
    """
    Base class of the UAT battery: a fresh database with the access model and
    the test DAGs, helpers to provision users and to log in through the MFA
    flow when the level requires it.

    Subclasses can set ``config_overrides`` to change settings that are read
    when the application is created (e.g. ``RATELIMIT_ENABLED``).
    """

    config_overrides = {}

    def create_app(self):
        return create_app(uat_env_name(**self.config_overrides))

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.mfa_secrets = {}

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    # Users

    def make_user(self, username, role_ids, password=None, email=None, **extra):
        """
        Creates a user straight in the database with the given role ids and
        returns it. The password must comply with the policy.
        """
        data = {
            "username": username,
            "email": email or f"{username}@example.com",
            "password": password or PASSWORDS.get(username, DEFAULT_PASSWORD),
            **extra,
        }
        user = UserModel(data)
        user.save()
        for role_id in role_ids:
            UserRoleModel({"user_id": user.id, "role_id": role_id}).save()
        return user

    @staticmethod
    def password_of(username):
        return PASSWORDS.get(username, DEFAULT_PASSWORD)

    # Login

    def login(self, username, password=None, totp_code=None, headers=None):
        """
        Raw POST /login/. Returns the response.
        """
        payload = {
            "username": username,
            "password": password or self.password_of(username),
        }
        if totp_code is not None:
            payload["totp_code"] = totp_code
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            headers={**JSON_HEADER, **(headers or {})},
        )

    def enroll_mfa(self, temp_token, username=None):
        """
        Completes the MFA enrollment with the temporary token. Returns the
        verify response (with ``token``, ``backup_codes``...).
        """
        setup = self.client.post(MFA_SETUP_URL, headers=auth_header(temp_token))
        self.assertEqual(200, setup.status_code, setup.json)
        secret = setup.json["secret"]
        if username is not None:
            self.mfa_secrets[username] = secret
        verify = self.client.post(
            MFA_VERIFY_URL,
            data=json.dumps({"totp_code": pyotp.TOTP(secret).now()}),
            headers=auth_header(temp_token),
        )
        self.assertEqual(200, verify.status_code, verify.json)
        verify.json["secret"] = secret
        return verify

    def totp_now(self, username):
        """
        Current TOTP code of an enrolled user. Clears the anti-replay counter
        first so that consecutive logins inside the same 30 s step work (the
        anti-replay guard itself is checked by case 2.5).
        """
        user = UserModel.get_one_user_by_username(username)
        user.totp_last_counter = None
        db.session.commit()
        return pyotp.TOTP(self.mfa_secrets[username]).now()

    def full_login(self, username, password=None):
        """
        Logs in completing the MFA step when the user has it (enrolls
        the user on the first login). Returns the full login response json
        (``token``, ``refresh_token``...).
        """
        password = password or self.password_of(username)
        response = self.login(username, password)
        self.assertEqual(200, response.status_code, response.json)
        body = response.json
        if body.get("mfa_setup_required"):
            body = self.enroll_mfa(body["temp_token"], username).json
        elif body.get("mfa_required"):
            response = self.login(username, password, self.totp_now(username))
            self.assertEqual(200, response.status_code, response.json)
            body = response.json
        self.assertIn("token", body)
        return body

    def token_of(self, username, password=None):
        return self.full_login(username, password)["token"]

    # Assertions and helpers by level

    def assert_invalid_token(self, response, message=None):
        """401 with the Bearer ``invalid_token`` challenge naming the error."""
        self.assertEqual(401, response.status_code, response.json)
        challenge = response.headers.get(WWW_AUTHENTICATE_HEADER, "")
        self.assertTrue(
            challenge.startswith(f'Bearer error="{INVALID_TOKEN_ERROR_CODE}"'),
            challenge,
        )
        self.assertIn(f'error_description="{response.json["error"]}"', challenge)
        if message is not None:
            self.assertEqual(message, response.json["error"])

    def ensure_mfa(self, username):
        """
        Leaves the user with MFA enrolled and the secret in ``mfa_secrets``:
        mandatory enrollment at level 3, voluntary one at levels 1 and 2.
        """
        if username in self.mfa_secrets:
            return
        response = self.login(username)
        self.assertEqual(200, response.status_code, response.json)
        if response.json.get("mfa_setup_required"):
            self.enroll_mfa(response.json["temp_token"], username)
            return
        self.assertIn("token", response.json)
        if int(current_app.config["MFA_ENABLED"]) != 1:
            self.fail(
                "MFA enrollment is disabled in this configuration: "
                "add MFA_ENROLLMENT_OVERRIDES to the test class"
            )
        self.enroll_mfa(response.json["token"], username)

    def lock_account(self, username, password="Wrong-password-0!"):
        """Fails the login LOGIN_MAX_ATTEMPTS times and checks the lock. Returns the attempts."""
        attempts = int(current_app.config["LOGIN_MAX_ATTEMPTS"])
        if attempts <= 0:
            self.fail(
                "the account lockout is off in this configuration: "
                "add LOCKOUT_OVERRIDES to the test class"
            )
        for _ in range(attempts):
            self.login(username, password)
        db.session.expire_all()
        self.assertTrue(UserModel.get_one_user_by_username(username).locked)
        return attempts

    @staticmethod
    def session_minutes():
        """Life in minutes of the token returned by the login of an interactive user."""
        if int(current_app.config["REFRESH_TOKEN_ENABLED"]) == 1:
            return int(current_app.config["ACCESS_TOKEN_DURATION_MINUTES"])
        return int(float(current_app.config["TOKEN_DURATION"]) * 60)

    @staticmethod
    def token_claims(token):
        return jwt.decode(
            token, current_app.config["SECRET_TOKEN_KEY"], algorithms=["HS256"]
        )

    # E-mail

    def fake_smtp(self):
        """
        Context manager that replaces the SMTP client with :class:`FakeSMTP`
        and configures the service e-mail settings. ``FakeSMTP.sent`` is
        emptied on entry.
        """
        FakeSMTP.sent = []
        current_app.config.update(
            SERVICE_EMAIL_ADDRESS="cornflow@example.com",
            SERVICE_EMAIL_PASSWORD="smtp-password",
            SERVICE_EMAIL_SERVER="smtp.example.com",
            SERVICE_EMAIL_PORT=465,
        )
        return patch("cornflow.shared.email.SMTP_SSL", FakeSMTP)
