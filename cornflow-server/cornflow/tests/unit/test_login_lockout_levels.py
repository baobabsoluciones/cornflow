"""
Tests of the lockout after failed logins by security level (task007):

- LOGIN_MAX_ATTEMPTS at 0 or lower (default at level 1) neither counts nor
  locks; accounts that were already locked stay locked;
- with LOGIN_MAX_ATTEMPTS above 0 (levels 2 and 3, and level 1 when set) the
  account is locked at the N-th consecutive failure, with no automatic unlock;
- the lock revokes session tokens, refresh sessions and the API keys (also the
  one superseded by a rotation still inside its grace window);
- the lock is audited once, not on every later failure of a locked account.

The expected messages are written in this file on purpose: they come from the
specification, not from the code under test.
"""

import json
import logging
import time
import unittest

import pyotp
from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.models import SessionModel, UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import SERVICE_ROLE, VIEWER_ROLE
from cornflow.tests.const import LOGIN_URL, PREFIX, USER_URL
from cornflow.tests.security_levels_support import SecurityLevelTestMixin

GENERIC_LOGIN_ERROR = "Invalid credentials"
BAD_TOTP_ERROR = "Invalid two-factor authentication code"
ACCOUNT_LOCKED_MESSAGE = (
    "The account is locked due to too many failed login attempts. "
    "Please contact an administrator to unlock it."
)
REVOKED_API_KEY_ERROR = "The API key has been revoked, please generate a new one"

USER_PASSWORD = "Kx9#tR2m!Qw7Zp"
SERVICE_PASSWORD = "Sv7&kM2x!Bd5Ln"
WRONG_PASSWORD = "Wrong#Password9!x"
JSON_HEADER = {"Content-Type": "application/json"}


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


class _AuditCapture(logging.Handler):
    """Captures the JSON records emitted on the cornflow.audit logger."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        try:
            self.records.append(json.loads(record.getMessage()))
        except (ValueError, TypeError):
            pass

    def by_event(self, event):
        return [r for r in self.records if r.get("event") == event]


class _LockoutApiCases:
    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        self.user = UserModel(
            {"username": "ana", "email": "ana@test.org", "password": USER_PASSWORD}
        )
        self.user.save()
        UserRoleModel({"user_id": self.user.id, "role_id": VIEWER_ROLE}).save()
        self.audit_logger = logging.getLogger("cornflow.audit")
        self._previous_level = self.audit_logger.level
        self.audit_logger.setLevel(logging.INFO)
        self.capture = _AuditCapture()
        self.audit_logger.addHandler(self.capture)

    def tearDown(self):
        self.audit_logger.removeHandler(self.capture)
        self.audit_logger.setLevel(self._previous_level)
        db.session.remove()
        db.drop_all()

    # helpers
    def login(self, username="ana", password=USER_PASSWORD, totp_code=None):
        body = {"username": username, "password": password}
        if totp_code is not None:
            body["totp_code"] = totp_code
        return self.client.post(
            LOGIN_URL, data=json.dumps(body), headers=JSON_HEADER
        )

    def fail_logins(self, n, username="ana"):
        return [self.login(username, WRONG_PASSWORD) for _ in range(n)]

    def user_row(self, username="ana"):
        db.session.expire_all()
        return UserModel.get_one_user_by_username(username)

    def get_me(self, token, user_id=None):
        return self.client.get(
            f"{USER_URL}{user_id or self.user.id}/", headers=auth_header(token)
        )

    def generate_api_key(self, token):
        return self.client.post(
            PREFIX + "/user/api-key/", data=json.dumps({}), headers=auth_header(token)
        )

    def enable_mfa(self, user=None):
        user = user or self.user_row()
        secret = pyotp.random_base32()
        user.set_totp_secret(secret)
        user.mfa_enabled = True
        user.save()
        return secret

    @staticmethod
    def wrong_totp(secret):
        # Outside the accepted window (+-1 step)
        return pyotp.TOTP(secret).at(time.time() - 600)

    def make_service_user(self):
        user = UserModel(
            {
                "username": "svc",
                "email": "svc@test.org",
                "password": SERVICE_PASSWORD,
            }
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": SERVICE_ROLE}).save()
        return user

    def assert_generic_failure(self, response):
        self.assertEqual(400, response.status_code, response.json)
        self.assertEqual(GENERIC_LOGIN_ERROR, response.json["error"])
        self.assertNotIn("error_code", response.json)

    def assert_locked_response(self, response):
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual(ACCOUNT_LOCKED_MESSAGE, response.json["error"])
        self.assertEqual("account_locked", response.json["error_code"])

    # cases common to every configuration
    def test_service_user_never_locked(self):
        self.make_service_user()
        for response in self.fail_logins(20, username="svc"):
            self.assertEqual(400, response.status_code)
        service = self.user_row("svc")
        self.assertEqual(0, service.failed_login_attempts)
        self.assertFalse(service.locked)
        response = self.login("svc", SERVICE_PASSWORD)
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)

    def test_successful_login_resets_counter(self):
        user = self.user_row()
        user.failed_login_attempts = 3
        user.save()
        response = self.login()
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(0, self.user_row().failed_login_attempts)

    def test_existing_lock_is_kept(self):
        user = self.user_row()
        user.locked = True
        user.failed_login_attempts = 5
        user.save()
        response = self.login()
        self.assert_locked_response(response)
        self.assertNotIn("platform", response.json["error"].lower())
        response = self.login(password=WRONG_PASSWORD)
        self.assert_generic_failure(response)
        self.assertTrue(self.user_row().locked)
        self.user_row().unlock_account()
        response = self.login()
        self.assertEqual(200, response.status_code, response.json)


class _NoLockoutCases(_LockoutApiCases):
    expected_max_attempts = 0

    def test_wrong_passwords_never_lock(self):
        for response in self.fail_logins(10):
            self.assert_generic_failure(response)
        user = self.user_row()
        self.assertEqual(0, user.failed_login_attempts)
        self.assertFalse(user.locked)
        self.assertEqual(200, self.login().status_code)

    def test_wrong_totp_never_locks(self):
        secret = self.enable_mfa()
        for _ in range(10):
            response = self.login(totp_code=self.wrong_totp(secret))
            self.assertEqual(400, response.status_code, response.json)
            self.assertEqual(BAD_TOTP_ERROR, response.json["error"])
        user = self.user_row()
        self.assertEqual(0, user.failed_login_attempts)
        self.assertFalse(user.locked)
        response = self.login(totp_code=pyotp.TOTP(secret).now())
        self.assertEqual(200, response.status_code, response.json)

    def test_failures_are_audited_without_lock(self):
        self.fail_logins(6)
        failures = self.capture.by_event("login.failure")
        self.assertEqual(6, len(failures))
        for record in failures:
            self.assertEqual("bad_password", record.get("reason"))
        self.assertEqual(0, len(self.capture.by_event("account.locked")))

    def test_failures_do_not_touch_tokens(self):
        token = self.login().json["token"]
        api_key = self.generate_api_key(token).json["api_key"]
        before = self.user_row()
        token_version = before.token_version
        api_key_version = before.api_key_version
        self.fail_logins(10)
        self.assertEqual(200, self.get_me(token).status_code)
        self.assertEqual(200, self.get_me(api_key).status_code)
        after = self.user_row()
        self.assertEqual(token_version, after.token_version)
        self.assertEqual(api_key_version, after.api_key_version)

    def test_lockout_helpers(self):
        self.assertFalse(UserModel.login_lockout_enabled())
        self.assertEqual(self.expected_max_attempts, UserModel.login_max_attempts())


class TestNoLockoutLevel1(_NoLockoutCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    expected_max_attempts = 0


class TestNoLockoutLevel1ExplicitZero(
    _NoLockoutCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    security_environ = {"LOGIN_MAX_ATTEMPTS": "0"}
    expected_max_attempts = 0


class TestNoLockoutLevel1Negative(_NoLockoutCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    security_environ = {"LOGIN_MAX_ATTEMPTS": "-1"}
    expected_max_attempts = -1


class _LockoutCases(_LockoutApiCases):
    max_attempts = 5

    def lock(self):
        responses = self.fail_logins(self.max_attempts)
        self.assertTrue(self.user_row().locked)
        return responses

    def test_locks_at_max_attempts(self):
        responses = self.fail_logins(self.max_attempts - 1)
        for response in responses:
            self.assert_generic_failure(response)
        user = self.user_row()
        self.assertFalse(user.locked)
        self.assertEqual(self.max_attempts - 1, user.failed_login_attempts)
        self.assert_generic_failure(self.login(password=WRONG_PASSWORD))
        self.assertTrue(self.user_row().locked)
        self.assert_locked_response(self.login())

    def test_lock_does_not_expire(self):
        self.lock()
        for _ in range(3):
            self.assert_locked_response(self.login())
        self.assertTrue(self.user_row().locked)

    def test_lock_revokes_session_token(self):
        token = self.login().json["token"]
        self.assertEqual(200, self.get_me(token).status_code)
        token_version = self.user_row().token_version
        self.lock()
        response = self.get_me(token)
        self.assertEqual(401, response.status_code)
        self.assertIn("WWW-Authenticate", response.headers)
        self.assertEqual(token_version + 1, self.user_row().token_version)

    def test_lock_revokes_api_key(self):
        token = self.login().json["token"]
        response = self.generate_api_key(token)
        self.assertEqual(201, response.status_code, response.json)
        api_key = response.json["api_key"]
        self.assertEqual(200, self.get_me(api_key).status_code)
        api_key_version = self.user_row().api_key_version
        self.lock()
        response = self.get_me(api_key)
        self.assertEqual(401, response.status_code)
        self.assertEqual(REVOKED_API_KEY_ERROR, response.json["error"])
        user = self.user_row()
        self.assertGreater(user.api_key_version, api_key_version)
        self.assertIsNone(user.api_key_issued_at)

    def test_lock_revokes_api_key_in_rotation_grace(self):
        token = self.login().json["token"]
        first = self.generate_api_key(token).json["api_key"]
        second = self.generate_api_key(token).json["api_key"]
        # Default grace window (60 minutes): both keys are valid
        self.assertEqual(200, self.get_me(first).status_code)
        self.assertEqual(200, self.get_me(second).status_code)
        self.lock()
        self.assertEqual(401, self.get_me(first).status_code)
        self.assertEqual(401, self.get_me(second).status_code)
        user = self.user_row()
        self.assertIsNone(user.api_key_previous_version)
        self.assertIsNone(user.api_key_grace_until)

    def test_wrong_totp_locks(self):
        secret = self.enable_mfa()
        for _ in range(self.max_attempts - 1):
            response = self.login(totp_code=self.wrong_totp(secret))
            self.assertEqual(400, response.status_code, response.json)
            self.assertEqual(BAD_TOTP_ERROR, response.json["error"])
        response = self.login(totp_code=self.wrong_totp(secret))
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("account_locked", response.json["error_code"])
        response = self.login(totp_code=pyotp.TOTP(secret).now())
        self.assertEqual(403, response.status_code, response.json)

    def test_password_and_totp_failures_add_up(self):
        secret = self.enable_mfa()
        self.fail_logins(self.max_attempts - 1)
        response = self.login(totp_code=self.wrong_totp(secret))
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("account_locked", response.json["error_code"])

    def test_success_resets_counter_before_lock(self):
        self.fail_logins(self.max_attempts - 1)
        response = self.login()
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(0, self.user_row().failed_login_attempts)
        self.fail_logins(self.max_attempts - 1)
        self.assertFalse(self.user_row().locked)

    def test_lock_is_audited_once(self):
        self.lock()
        before = self.user_row()
        token_version = before.token_version
        api_key_version = before.api_key_version
        self.fail_logins(2)
        locked = self.capture.by_event("account.locked")
        self.assertEqual(1, len(locked))
        self.assertEqual(self.max_attempts, locked[0].get("attempts"))
        self.assertEqual("ana", locked[0].get("target"))
        self.assertEqual("locked", locked[0].get("outcome"))
        self.assertEqual(
            self.max_attempts + 2, len(self.capture.by_event("login.failure"))
        )
        after = self.user_row()
        self.assertEqual(token_version, after.token_version)
        self.assertEqual(api_key_version, after.api_key_version)
        self.assertEqual(self.max_attempts + 2, after.failed_login_attempts)

    def test_lockout_helpers(self):
        self.assertTrue(UserModel.login_lockout_enabled())
        self.assertEqual(self.max_attempts, UserModel.login_max_attempts())


class TestLockoutLevel1WithMaxAttempts(
    _LockoutCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    security_environ = {"LOGIN_MAX_ATTEMPTS": "3"}
    max_attempts = 3


class TestLockoutLevel2(_LockoutCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    max_attempts = 5


class TestLockoutLevel2CustomMaxAttempts(
    _LockoutCases, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    security_environ = {"LOGIN_MAX_ATTEMPTS": "3"}
    max_attempts = 3


class TestLockoutLevel3(_LockoutCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    # Users without MFA get a token; MFA_ENABLED stays on
    config_overrides = {"MFA_REQUIRED": 0}
    max_attempts = 5

    def test_lock_revokes_refresh_session(self):
        response = self.login()
        self.assertEqual(200, response.status_code, response.json)
        refresh_token = response.json["refresh_token"]
        self.lock()
        response = self.client.post(
            PREFIX + "/token/refresh/",
            data=json.dumps({"refresh_token": refresh_token}),
            headers=JSON_HEADER,
        )
        self.assertEqual(401, response.status_code)
        db.session.expire_all()
        sessions = SessionModel.query.filter_by(user_id=self.user.id).all()
        self.assertTrue(sessions)
        for session in sessions:
            self.assertTrue(session.revoked)


class TestLockoutLevel2AdjustedMaxAttempts(
    _LockoutApiCases, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    security_environ = {"LOGIN_MAX_ATTEMPTS": "20"}

    def test_locks_at_ten(self):
        self.fail_logins(9)
        self.assertFalse(self.user_row().locked)
        self.fail_logins(1)
        self.assertTrue(self.user_row().locked)


class TestLockoutSettingFallback(TestCase):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_default_when_setting_is_missing(self):
        previous = current_app.config.pop("LOGIN_MAX_ATTEMPTS")
        try:
            self.assertEqual(5, UserModel.login_max_attempts())
        finally:
            current_app.config["LOGIN_MAX_ATTEMPTS"] = previous


if __name__ == "__main__":
    unittest.main()
