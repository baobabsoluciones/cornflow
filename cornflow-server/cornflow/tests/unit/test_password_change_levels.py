"""
Tests of the forced password change and the password rotation by security
level (task006):

- from level 2 the passwords set by an admin (signup or edit) and the
  temporary recovery passwords are single-use; level 1 does not flag them;
- a password flagged with ``pwd_change_required`` only blocks from level 2
  (whatever ``PWD_ROTATION_ENFORCE`` is); level 1 ignores the flag but keeps it;
- an expired password (older than ``PWD_ROTATION_TIME`` days) only blocks with
  ``PWD_ROTATION_ENFORCE=1`` (default of level 3);
- ``change_password`` in the login: age at level 1, flag or age from level 2;
- the service user and the users of an external provider are exempt;
- ``--force-password-change`` of the CLI keeps the flag at every level and
  warns when the level ignores it.

The expected values are written in this file on purpose: they come from the
specification (table 8.4), not from the code under test.
"""

import json
import logging
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from click.testing import CliRunner
from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.commands.access import access_init_command
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db, validators
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLATFORM_ADMIN_ROLE,
    SERVICE_ROLE,
    VIEWER_ROLE,
)
from cornflow.shared.email import get_password_recover_email
from cornflow.tests.const import (
    INSTANCE_URL,
    LOGIN_URL,
    RECOVER_PASSWORD_URL,
    SIGNUP_URL,
    TOKEN_URL,
    USER_URL,
)
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    security_level_config,
)

P1 = "Kx9#tR2m!Qw7Zp"
P2 = "Hd6$vNc4&Ye2Bs"
P3 = "Mv4#qL8n!Zr5Tw"
GRANITO = "Granito-Vela-Oruga7"
JSON_HEADER = {"Content-Type": "application/json"}

FLAGGED = "flagged"
EXPIRED = "expired"


def _overrides(level, **extra):
    """Config overrides common to the three levels (no MFA at level 3)."""
    overrides = dict(extra)
    if level == 3:
        overrides.setdefault("MFA_REQUIRED", 0)
    return overrides


def _flag_enforced():
    return validators.password_change_flag_enforced()


def _rotation_enforced():
    return validators.password_rotation_enforced()


# --------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------
class _Base:
    """Helpers shared by the cases that need the application."""

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user(
        self, username, password, role=VIEWER_ROLE, flagged=False, age_days=None
    ):
        user = UserModel(
            {"username": username, "email": f"{username}@test.org", "password": password}
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role}).save()
        # Directly in the database, as the migration does
        if flagged:
            user.pwd_change_required = True
        if age_days is not None:
            user.pwd_last_change = datetime.now(timezone.utc) - timedelta(
                days=age_days
            )
        if flagged or age_days is not None:
            db.session.commit()
        return user

    def create_external_user(self, username):
        user = self.create_user(username, P1, flagged=True)
        user.password = None
        db.session.commit()
        return user, Auth.generate_token(user.id)

    def login(self, username, password, expected=200):
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": password}),
            headers=JSON_HEADER,
        )
        self.assertEqual(expected, response.status_code, response.json)
        return response.json

    def headers(self, token):
        return {**JSON_HEADER, "Authorization": "Bearer " + token}

    def get_instances(self, token):
        return self.client.get(INSTANCE_URL, headers=self.headers(token))

    def get_own(self, token, user_id):
        return self.client.get(USER_URL + f"{user_id}/", headers=self.headers(token))

    def put_user(self, token, user_id, payload):
        return self.client.put(
            USER_URL + f"{user_id}/",
            data=json.dumps(payload),
            headers=self.headers(token),
        )

    def assert_blocked(self, response):
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("password_rotation", (response.json or {}).get("error_code"))

    def assert_access(self, response):
        self.assertEqual(200, response.status_code, response.json)

    def assert_access_is(self, blocked, response):
        if blocked:
            self.assert_blocked(response)
        else:
            self.assert_access(response)

    def flag_in_db(self, user_id):
        db.session.remove()
        return UserModel.get_one_user(user_id).pwd_change_required

    def change_own_password(self, token, user_id, current, new):
        response = self.put_user(
            token, user_id, {"password": new, "current_password": current}
        )
        self.assertEqual(200, response.status_code, response.json)


# --------------------------------------------------------------------------
# A. Without application context
# --------------------------------------------------------------------------
class TestPasswordChangeHelpersWithoutAppContext(unittest.TestCase):
    def test_flag_enforced(self):
        self.assertTrue(_flag_enforced())

    def test_rotation_enforced(self):
        self.assertTrue(_rotation_enforced())


# --------------------------------------------------------------------------
# B. Helpers by level
# --------------------------------------------------------------------------
class _HelperCases(_Base):
    expect_flag = None
    expect_rotation = None

    def test_flag_enforced(self):
        self.assertEqual(self.expect_flag, _flag_enforced())

    def test_rotation_enforced(self):
        self.assertEqual(self.expect_rotation, _rotation_enforced())

    def test_blocking_reason(self):
        flagged = self.create_user("flagged", P1, flagged=True)
        old = self.create_user("old", P1, age_days=200)
        both = self.create_user("both", P1, flagged=True, age_days=200)
        clean = self.create_user("clean", P1)

        flagged_reason = FLAGGED if self.expect_flag else None
        old_reason = EXPIRED if self.expect_rotation else None
        both_reason = FLAGGED if self.expect_flag else old_reason

        self.assertEqual(flagged_reason, Auth.password_change_blocking_reason(flagged))
        self.assertEqual(old_reason, Auth.password_change_blocking_reason(old))
        self.assertEqual(both_reason, Auth.password_change_blocking_reason(both))
        self.assertIsNone(Auth.password_change_blocking_reason(clean))

    def test_flag_applies(self):
        flagged = self.create_user("flagged", P1, flagged=True)
        clean = self.create_user("clean", P1)
        self.assertEqual(self.expect_flag, Auth.password_change_flag_applies(flagged))
        self.assertFalse(Auth.password_change_flag_applies(clean))


class TestPasswordChangeHelpersLevel1(_HelperCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    expect_flag = False
    expect_rotation = False


class TestPasswordChangeHelpersLevel2(_HelperCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    expect_flag = True
    expect_rotation = False


class TestPasswordChangeHelpersLevel3(_HelperCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3)
    expect_flag = True
    expect_rotation = True


class TestPasswordChangeHelpersLevel1RotationOn(
    _HelperCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(1, PWD_ROTATION_ENFORCE=1)
    expect_flag = False
    expect_rotation = True


class TestPasswordChangeHelpersLevel3RotationOff(
    _HelperCases, SecurityLevelTestMixin, TestCase
):
    security_level = 3
    config_overrides = _overrides(3, PWD_ROTATION_ENFORCE=0)
    expect_flag = True
    expect_rotation = False


# --------------------------------------------------------------------------
# C. Signup by an admin
# --------------------------------------------------------------------------
class _SignupCases(_Base):
    signup_activated = None
    actor_role = None
    expect_flag = None

    def setUp(self):
        super().setUp()
        self.actor = self.create_user("actor", P3, role=self.actor_role)

    def signup(self, username="newuser", password=P1):
        token = Auth.generate_token(self.actor.id)
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": username,
                    "email": f"{username}@test.org",
                    "password": password,
                }
            ),
            headers=self.headers(token),
        )

    def test_signup_by_admin(self):
        response = self.signup()
        self.assertEqual(201, response.status_code, response.json)
        new_id = response.json["id"]
        self.assertEqual(self.expect_flag, self.flag_in_db(new_id))

        body = self.login("newuser", P1)
        self.assertEqual(self.expect_flag, body["change_password"])
        token = body["token"]
        self.assert_access_is(self.expect_flag, self.get_instances(token))
        self.assert_access(self.get_own(token, new_id))

    def test_new_user_changes_password(self):
        new_id = self.signup().json["id"]
        token = self.login("newuser", P1)["token"]
        self.change_own_password(token, new_id, P1, P2)
        self.assertFalse(self.flag_in_db(new_id))
        body = self.login("newuser", P2)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))


class TestSignupFlagLevel1(_SignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, SIGNUP_ACTIVATED=2)
    actor_role = ADMIN_ROLE
    expect_flag = False


class TestSignupFlagLevel1PlatformOnly(_SignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, SIGNUP_ACTIVATED=3)
    actor_role = PLATFORM_ADMIN_ROLE
    expect_flag = False


class TestSignupFlagLevel2(_SignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, SIGNUP_ACTIVATED=3)
    actor_role = PLATFORM_ADMIN_ROLE
    expect_flag = True


class TestSignupFlagLevel2WithAuth(_SignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, SIGNUP_ACTIVATED=2)
    actor_role = PLATFORM_ADMIN_ROLE
    expect_flag = True


class TestSignupFlagLevel3(_SignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3, SIGNUP_ACTIVATED=3)
    actor_role = PLATFORM_ADMIN_ROLE
    expect_flag = True


class _OpenSignupCases(_Base):
    def test_open_signup_never_flags(self):
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {"username": "selfmade", "email": "selfmade@test.org", "password": P1}
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(201, response.status_code, response.json)
        self.assertFalse(self.flag_in_db(response.json["id"]))


class TestOpenSignupLevel1(_OpenSignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, SIGNUP_ACTIVATED=1)


class TestOpenSignupLevel2(_OpenSignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, SIGNUP_ACTIVATED=1)


class TestOpenSignupLevel3(_OpenSignupCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3, SIGNUP_ACTIVATED=1)


# --------------------------------------------------------------------------
# D. Password set by an admin
# --------------------------------------------------------------------------
class _AdminSetPasswordCases(_Base):
    expect_flag = None

    def setUp(self):
        super().setUp()
        self.create_user("boss", P1, role=ADMIN_ROLE)
        self.ana = self.create_user("ana", P2)

    def admin_sets_password(self):
        token = self.login("boss", P1)["token"]
        response = self.put_user(token, self.ana.id, {"password": GRANITO})
        self.assertEqual(200, response.status_code, response.json)

    def test_admin_sets_password(self):
        self.admin_sets_password()
        self.assertEqual(self.expect_flag, self.flag_in_db(self.ana.id))

        body = self.login("ana", GRANITO)
        self.assertEqual(self.expect_flag, body["change_password"])
        token = body["token"]
        self.assert_access_is(self.expect_flag, self.get_instances(token))
        self.assert_access(self.get_own(token, self.ana.id))

    def test_user_changes_the_password_set_by_the_admin(self):
        self.admin_sets_password()
        token = self.login("ana", GRANITO)["token"]
        self.change_own_password(token, self.ana.id, GRANITO, P3)
        self.assertFalse(self.flag_in_db(self.ana.id))
        body = self.login("ana", P3)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))

    def test_previous_flag_follows_the_level(self):
        # Flagged before (as the migration does): at level 1 the new password
        # is a normal one and clears the flag, from level 2 it is single-use
        user = self.create_user("marked", P2, flagged=True)
        token = self.login("boss", P1)["token"]
        response = self.put_user(token, user.id, {"password": GRANITO})
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(self.expect_flag, self.flag_in_db(user.id))


class TestAdminSetPasswordLevel1(_AdminSetPasswordCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    expect_flag = False


class TestAdminSetPasswordLevel2(_AdminSetPasswordCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    expect_flag = True


class TestAdminSetPasswordLevel3(_AdminSetPasswordCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3)
    expect_flag = True


# --------------------------------------------------------------------------
# E. Recovery with a temporary password
# --------------------------------------------------------------------------
class _RecoverCases(_Base):
    expect_flag = None

    def setUp(self):
        super().setUp()
        self.ana = self.create_user("ana", P1)

    def recover(self):
        with mock.patch("cornflow.endpoints.user.send_email_to") as send_email, mock.patch(
            "cornflow.endpoints.user.get_password_recover_email",
            wraps=get_password_recover_email,
        ) as recover_email:
            response = self.client.put(
                RECOVER_PASSWORD_URL,
                data=json.dumps({"email": "ana@test.org"}),
                headers=JSON_HEADER,
            )
        self.assertEqual(200, response.status_code, response.json)
        send_email.assert_called_once()
        return recover_email.call_args.kwargs["temp_password"]

    def test_temporary_password(self):
        temp = self.recover()
        self.login("ana", P1, expected=400)
        self.assertEqual(self.expect_flag, self.flag_in_db(self.ana.id))

        body = self.login("ana", temp)
        self.assertEqual(self.expect_flag, body["change_password"])
        self.assert_access_is(self.expect_flag, self.get_instances(body["token"]))

    def test_temporary_password_can_be_reused_when_not_flagged(self):
        temp = self.recover()
        self.login("ana", temp)
        body = self.login("ana", temp)
        self.assertEqual(self.expect_flag, body["change_password"])
        self.assert_access_is(self.expect_flag, self.get_instances(body["token"]))

    def test_user_changes_the_temporary_password(self):
        temp = self.recover()
        token = self.login("ana", temp)["token"]
        self.change_own_password(token, self.ana.id, temp, P3)
        self.assertFalse(self.flag_in_db(self.ana.id))
        body = self.login("ana", P3)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))

    def test_previous_flag_follows_the_level(self):
        user = self.create_user("marked", P2, flagged=True)
        with mock.patch("cornflow.endpoints.user.send_email_to"):
            response = self.client.put(
                RECOVER_PASSWORD_URL,
                data=json.dumps({"email": "marked@test.org"}),
                headers=JSON_HEADER,
            )
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(self.expect_flag, self.flag_in_db(user.id))


# LOGIN_MAX_ATTEMPTS is pinned high so the failed login with the old password
# does not trigger the lockout (a separate concern, owned by the lockout task).
_EMAIL_OVERRIDES = dict(
    LOGIN_MAX_ATTEMPTS=50,
    SERVICE_EMAIL_ADDRESS="cornflow@test.com",
    SERVICE_EMAIL_PASSWORD="not-used",
    SERVICE_EMAIL_SERVER="smtp.test.com",
    SERVICE_EMAIL_PORT=465,
)


class TestRecoverLevel1(_RecoverCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, **_EMAIL_OVERRIDES)
    expect_flag = False


class TestRecoverLevel2(_RecoverCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, **_EMAIL_OVERRIDES)
    expect_flag = True


class TestRecoverLevel3(_RecoverCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3, **_EMAIL_OVERRIDES)
    expect_flag = True


# --------------------------------------------------------------------------
# F. Existing flags (migration, CLI)
# --------------------------------------------------------------------------
class _ExistingFlagCases(_Base):
    expect_flag = None

    def setUp(self):
        super().setUp()
        self.ana = self.create_user("ana", P1, flagged=True)

    def test_login_and_access(self):
        body = self.login("ana", P1)
        self.assertEqual(self.expect_flag, body["change_password"])
        token = body["token"]
        self.assert_access_is(self.expect_flag, self.get_instances(token))
        # The flag is data: neither the login nor the requests touch it
        self.assertTrue(self.flag_in_db(self.ana.id))
        response = self.get_own(token, self.ana.id)
        self.assert_access(response)
        self.assertTrue(response.json["pwd_change_required"])

    def test_own_change_clears_the_flag(self):
        token = self.login("ana", P1)["token"]
        self.change_own_password(token, self.ana.id, P1, P2)
        self.assertFalse(self.flag_in_db(self.ana.id))
        body = self.login("ana", P2)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))

    def test_flag_applies_to_an_issued_token(self):
        other = self.create_user("clean", P1)
        token = self.login("clean", P1)["token"]
        self.assert_access(self.get_instances(token))
        other.pwd_change_required = True
        db.session.commit()
        self.assert_access_is(self.expect_flag, self.get_instances(token))

    def test_allowed_endpoints(self):
        other = self.create_user("other", P2)
        token = self.login("ana", P1)["token"]
        self.assert_access(self.get_own(token, self.ana.id))
        self.assert_access(self.client.get(TOKEN_URL, headers=self.headers(token)))
        response = self.put_user(token, other.id, {"password": P3})
        self.assertEqual(403, response.status_code)
        if self.expect_flag:
            self.assert_blocked(response)
        else:
            self.assertNotEqual(
                "password_rotation", response.json.get("error_code"), response.json
            )
        if self.expect_flag:
            # user-detail of another user stays blocked too
            self.assert_blocked(self.get_own(token, other.id))


class TestExistingFlagLevel1(_ExistingFlagCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    expect_flag = False

    def test_raising_the_level_applies_the_flag(self):
        token = self.login("ana", P1)["token"]
        self.assert_access(self.get_instances(token))
        previous = current_app.config["SECURITY_LEVEL"]
        current_app.config["SECURITY_LEVEL"] = 2
        try:
            self.assert_blocked(self.get_instances(token))
            self.assertTrue(self.login("ana", P1)["change_password"])
        finally:
            current_app.config["SECURITY_LEVEL"] = previous


class TestExistingFlagLevel1RotationOn(
    _ExistingFlagCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(1, PWD_ROTATION_ENFORCE=1)
    expect_flag = False


class TestExistingFlagLevel2(_ExistingFlagCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    expect_flag = True


class TestExistingFlagLevel2RotationOff(
    _ExistingFlagCases, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    config_overrides = _overrides(2, PWD_ROTATION_ENFORCE=0)
    expect_flag = True


class TestExistingFlagLevel3(_ExistingFlagCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3)
    expect_flag = True


class TestExistingFlagLevel3RotationOff(
    _ExistingFlagCases, SecurityLevelTestMixin, TestCase
):
    security_level = 3
    config_overrides = _overrides(3, PWD_ROTATION_ENFORCE=0)
    expect_flag = True


# --------------------------------------------------------------------------
# G. Expiration by time
# --------------------------------------------------------------------------
class _AgeCases(_Base):
    rotation_time = 120
    expect_block = None

    def setUp(self):
        super().setUp()
        self.old_days = self.rotation_time + 80
        self.recent_days = self.rotation_time - 20
        self.ana = self.create_user("ana", P1, age_days=self.old_days)
        self.beto = self.create_user("beto", P1, age_days=self.recent_days)

    def test_old_password(self):
        body = self.login("ana", P1)
        self.assertTrue(body["change_password"])
        token = body["token"]
        self.assert_access_is(self.expect_block, self.get_instances(token))
        self.assert_access(self.get_own(token, self.ana.id))

    def test_recent_password(self):
        body = self.login("beto", P1)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))

    def test_change_restores_the_access(self):
        token = self.login("ana", P1)["token"]
        self.change_own_password(token, self.ana.id, P1, P2)
        body = self.login("ana", P2)
        self.assertFalse(body["change_password"])
        self.assert_access(self.get_instances(body["token"]))

    def test_limit_case(self):
        over = self.create_user("over", P1, age_days=self.rotation_time + 1)
        under = self.create_user("under", P1, age_days=self.rotation_time - 1)
        token = self.login("over", P1)["token"]
        self.assert_access_is(self.expect_block, self.get_instances(token))
        token = self.login("under", P1)["token"]
        self.assert_access(self.get_instances(token))
        self.assertIsNotNone(over)
        self.assertIsNotNone(under)


class TestAgeLevel1(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    expect_block = False


class TestAgeLevel2(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    expect_block = False


class TestAgeLevel3(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3)
    expect_block = True


class TestAgeLevel1RotationOn(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, PWD_ROTATION_ENFORCE=1)
    expect_block = True


class TestAgeLevel2RotationOn(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, PWD_ROTATION_ENFORCE=1)
    expect_block = True


class TestAgeLevel3RotationOff(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3, PWD_ROTATION_ENFORCE=0)
    expect_block = False


class TestAgeLevel1ShortRotationTime(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, PWD_ROTATION_TIME=30)
    rotation_time = 30
    expect_block = False


class TestAgeLevel3ShortRotationTime(_AgeCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3, PWD_ROTATION_TIME=30)
    rotation_time = 30
    expect_block = True


# --------------------------------------------------------------------------
# H. Exempt users
# --------------------------------------------------------------------------
class _ExemptCases(_Base):
    # Whether a viewer flagged and 400 days old is blocked
    viewer_blocked = None

    def test_service_user(self):
        self.create_user(
            "service", P1, role=SERVICE_ROLE, flagged=True, age_days=400
        )
        token = self.login("service", P1)["token"]
        self.assert_access(self.get_instances(token))

    def test_external_provider_user(self):
        _, token = self.create_external_user("external")
        self.assert_access(self.get_instances(token))

    def test_viewer_with_the_same_state(self):
        self.create_user("viewer", P1, flagged=True, age_days=400)
        token = self.login("viewer", P1)["token"]
        self.assert_access_is(self.viewer_blocked, self.get_instances(token))


class TestExemptLevel1(_ExemptCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    viewer_blocked = False


class TestExemptLevel1RotationOn(_ExemptCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(1, PWD_ROTATION_ENFORCE=1)
    viewer_blocked = True


class TestExemptLevel2(_ExemptCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    viewer_blocked = True


class TestExemptLevel2RotationOn(_ExemptCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(2, PWD_ROTATION_ENFORCE=1)
    viewer_blocked = True


class TestExemptLevel3(_ExemptCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(3)
    viewer_blocked = True


# --------------------------------------------------------------------------
# I. CLI --force-password-change
# --------------------------------------------------------------------------
class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append((record.levelno, record.getMessage()))


class TestForcePasswordChangeCliByLevel(TestCase):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_viewer(self, level, username, force=True, extra_args=None):
        name = security_level_config(level, **_overrides(level))
        args = [
            "users",
            "create",
            "viewer",
            "-u",
            username,
            "-p",
            GRANITO,
            "-e",
            f"{username}@test.org",
        ]
        if force:
            args.append("--force-password-change")
        args.extend(extra_args or [])
        handler = _ListHandler()
        logger = logging.getLogger("cornflow.app")
        logger.addHandler(handler)
        try:
            with mock.patch.dict(os.environ, {"FLASK_ENV": name}):
                result = CliRunner().invoke(cli, args)
        finally:
            logger.removeHandler(handler)
        ignored = [
            msg
            for levelno, msg in handler.messages
            if levelno >= logging.WARNING and "ignores the flag" in msg
        ]
        return result, ignored

    def flag(self, username):
        db.session.remove()
        return UserModel.get_one_user_by_username(username).pwd_change_required

    def test_flag_is_kept_at_every_level(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                username = f"forced{level}"
                result, _ = self.create_viewer(level, username)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertTrue(self.flag(username))

    def test_level_1_warns_that_the_flag_is_ignored(self):
        result, ignored = self.create_viewer(1, "forced1")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(1, len(ignored), ignored)
        self.assertIn("security level 2", ignored[0])
        self.assertIn("forced1", ignored[0])

    def test_levels_2_and_3_do_not_warn(self):
        for level in (2, 3):
            with self.subTest(level=level):
                result, ignored = self.create_viewer(level, f"forced{level}")
                self.assertEqual(0, result.exit_code, result.output)
                self.assertEqual([], ignored)

    def test_without_the_option_there_is_no_flag_and_no_warning(self):
        result, ignored = self.create_viewer(1, "plain1", force=False)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertFalse(self.flag("plain1"))
        self.assertEqual([], ignored)

    def test_help_mentions_the_security_level(self):
        result = CliRunner().invoke(cli, ["users", "create", "viewer", "--help"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("security level 2", " ".join(result.output.split()))
