"""
Shared support for the server UAT battery of the security hardening
(``cornflow/tests/unit/test_uat_hardening_*.py``).

Each test of the battery is named after the id of its case in the UAT sheet
(``test_uat_6_5_...`` covers case 6.5) and runs against one of two profiles,
selected with the ``CORNFLOW_UAT_PROFILE`` environment variable:

- ``strict`` (default): the hardened defaults of a production deployment.
  The expected behaviour is the one written in the UAT sheet.
- ``relaxed``: the relaxed profile documented in ``docs/source/deploy/access.rst``
  for projects that do not need the full hardening. The relaxed controls
  must behave as relaxed and every other control must keep working.

Run the battery in both profiles::

    CORNFLOW_UAT_PROFILE=strict python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"
    CORNFLOW_UAT_PROFILE=relaxed python -m unittest discover -s cornflow/tests/unit -p "test_uat_hardening_*.py"

The cases the kit could not run are covered too: e-mail with the SMTP client
replaced by an in-process fake (:class:`FakeSMTP`), TLS through the
``X-Forwarded-Proto`` header and session windows with a simulated clock
(``freezegun``). The cases that can only be checked in the web client are
skipped with :func:`ui_only` and belong to the cornflow-ui battery.
"""

import json
import os
import unittest
from unittest.mock import patch

import pyotp
from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.config import Testing, app_config
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import SIGNUP_WITH_AUTH, SIGNUP_WITH_NO_AUTH
from cornflow.tests.const import LOGIN_URL, PREFIX

MFA_SETUP_URL = PREFIX + "/mfa/setup/"
MFA_VERIFY_URL = PREFIX + "/mfa/verify/"

STRICT = "strict"
RELAXED = "relaxed"

PROFILE = os.getenv("CORNFLOW_UAT_PROFILE", STRICT).strip().lower()
if PROFILE not in (STRICT, RELAXED):
    raise ValueError(
        f"CORNFLOW_UAT_PROFILE must be '{STRICT}' or '{RELAXED}', not '{PROFILE}'"
    )

# Hardening settings of each profile. The strict one reproduces the defaults
# of a production deployment; the relaxed one is the profile documented for
# less demanding projects. Everything not listed here (password policy
# floors, reuse detection, API key scope, platform roles, audit...) is the
# same in both profiles because it must never be relaxed.
PROFILES = {
    STRICT: {
        "MFA_REQUIRED": 1,
        "SIGNUP_ACTIVATED": SIGNUP_WITH_AUTH,
        "LOGIN_MAX_ATTEMPTS": 5,
        "RATELIMIT_LOGIN": "10 per minute",
        "RATELIMIT_RECOVER": "5 per hour",
        "REFRESH_TOKEN_ENABLED": 1,
        "ACCESS_TOKEN_DURATION_MINUTES": 15,
        "REFRESH_TOKEN_INACTIVITY_MINUTES": 30,
        "REFRESH_TOKEN_ABSOLUTE_HOURS": 12,
        "PERSONAL_TOKEN_ENABLED": 1,
        "API_KEY_STEPUP_TOTP": 1,
        "API_KEY_ROTATION_GRACE_MINUTES": 60,
        "PWD_ROTATION_TIME": 120,
        "HSTS_ENABLED": 1,
        "DOCS_ENABLED": 0,
        "CORS_ORIGINS": "",
    },
    RELAXED: {
        "MFA_REQUIRED": 0,
        "SIGNUP_ACTIVATED": SIGNUP_WITH_NO_AUTH,
        "LOGIN_MAX_ATTEMPTS": 10,
        "RATELIMIT_LOGIN": "30 per minute",
        "RATELIMIT_RECOVER": "20 per hour",
        "REFRESH_TOKEN_ENABLED": 1,
        "ACCESS_TOKEN_DURATION_MINUTES": 60,
        "REFRESH_TOKEN_INACTIVITY_MINUTES": 480,
        "REFRESH_TOKEN_ABSOLUTE_HOURS": 24,
        "PERSONAL_TOKEN_ENABLED": 1,
        "API_KEY_STEPUP_TOTP": 0,
        "API_KEY_ROTATION_GRACE_MINUTES": 1440,
        "PWD_ROTATION_TIME": 365,
        "HSTS_ENABLED": 0,
        "DOCS_ENABLED": 1,
        "CORS_ORIGINS": "",
    },
}

SETTINGS = PROFILES[PROFILE]

JSON_HEADER = {"Content-Type": "application/json"}

# Passwords that comply with the policy, one per user of the battery
PASSWORDS = {
    "cfadmin": "Kd8-rVt.Nq2Wp5",
    "service_user": "Xq7-mBv.Ld9Rn2",
    "cfplatform": "Zc4-hJm.Bt6Vx9",
}
DEFAULT_PASSWORD = "Gv5-pLx.Wr8Tm3"


def is_relaxed() -> bool:
    return PROFILE == RELAXED


def is_strict() -> bool:
    return PROFILE == STRICT


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


def profile_env_name(**overrides) -> str:
    """
    Registers (once) a configuration class with the settings of the active
    profile plus the given overrides and returns its name for create_app.
    """
    settings = {**SETTINGS, **overrides}
    key = "uat-" + PROFILE + "-" + json.dumps(settings, sort_keys=True)
    if key not in app_config:
        attrs = dict(settings)
        # Rate limiting is enabled only by the cases that check it, so that
        # the many logins of the battery are not throttled.
        attrs.setdefault("RATELIMIT_ENABLED", 0)
        app_config[key] = type("UatProfileConfig", (Testing,), attrs)
    return key


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
    flow when the profile requires it.

    Subclasses can set ``config_overrides`` to change settings that are read
    when the application is created (e.g. ``RATELIMIT_ENABLED``).
    """

    config_overrides = {}

    def create_app(self):
        return create_app(profile_env_name(**self.config_overrides))

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
        Logs in completing the MFA step when the profile requires it (enrolls
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


def pending_fix(commit: str):
    """
    Marks a case whose fix lives in a commit of
    ``feature/hardening-uat-fixes`` that is not integrated in this branch yet:
    the test asserts the behaviour of the UAT sheet and is an expected
    failure until the commit is integrated (then it reports an unexpected
    success and the marker must be removed).
    """

    def decorator(func):
        func.pending_fix = commit
        return unittest.expectedFailure(func)

    return decorator
