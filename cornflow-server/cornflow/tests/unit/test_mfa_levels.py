"""
Tests of the voluntary MFA enrollment that depends on MFA_ENABLED (task009):

- with MFA_ENABLED off (default of levels 1 and 2) POST /mfa/setup/ and
  POST /mfa/verify/ stay registered but answer 501 and write nothing;
- with MFA_ENABLED=1 (default of level 3) they work as before, also in the
  enrollment during the login when MFA_REQUIRED=1;
- users that already have MFA keep being asked for their code, and the MFA
  reset stays available whatever the value;
- the TOTP codes of the API keys and of the platform roles are only asked from
  users with MFA and only when their variable is 1.

The expected messages are written in this file on purpose: they come from the
specification, not from the code under test. No configuration breaks the
startup condition of MFA_REQUIRED, API_KEY_STEPUP_TOTP and
PLATFORM_ROLE_STEPUP_TOTP needing MFA_ENABLED=1.
"""

import json
import secrets
import time
import unittest

import pyotp
from flask import current_app
from flask_testing import TestCase

from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import MFABackupCodeModel, UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_PLANNER_ROLE,
    PLATFORM_VIEWER_ROLE,
    SERVICE_ROLE,
    TOKEN_PURPOSE_MFA_SETUP,
    TOKEN_PURPOSE_PWD_RESET,
    VIEWER_ROLE,
)
from cornflow.tests.const import LOGIN_URL, PREFIX, USER_URL
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    build_security_level_config,
)

PASSWORD = "Kx9#tR2m!Qw7Zp"  # valid at the three levels
MFA_SETUP_URL = PREFIX + "/mfa/setup/"
MFA_VERIFY_URL = PREFIX + "/mfa/verify/"
API_KEY_URL = PREFIX + "/user/api-key/"
USER_ROLE_URL = PREFIX + "/user/role/"
DISABLED_MESSAGE = (
    "Two-factor authentication enrollment is disabled on this deployment"
)
BAD_TOTP_ERROR = "Invalid two-factor authentication code"
API_KEY_STEPUP_ERROR = (
    "A valid two-factor authentication code is required to generate an API key"
)
ROLE_STEPUP_ERROR = (
    "A valid two-factor authentication code is required to grant a platform role"
)
RESET_MESSAGE = "The two-factor authentication has been reset"
API_KEY_REVOKED_ERROR = "The API key has been revoked, please generate a new one"
JSON_HEADER = {"Content-Type": "application/json"}
# Level 3 without MFA enrollment: the three dependants must be off too
LEVEL3_WITHOUT_ENROLLMENT = {
    "MFA_ENABLED": 0,
    "MFA_REQUIRED": 0,
    "API_KEY_STEPUP_TOTP": 0,
    "PLATFORM_ROLE_STEPUP_TOTP": 0,
}
ALL_ROLES = (
    VIEWER_ROLE,
    PLANNER_ROLE,
    ADMIN_ROLE,
    SERVICE_ROLE,
    PLATFORM_VIEWER_ROLE,
    PLATFORM_PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
)


def auth_header(token):
    return {**JSON_HEADER, "Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------
class _MfaLevelTestBase(SecurityLevelTestMixin, TestCase):
    """Helpers shared by the cases that need the application (no test_ methods)."""

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user(self, username, role_id=PLANNER_ROLE):
        # Directly in the database: no /signup/, so neither SIGNUP_ACTIVATED nor
        # the one-time password mark get in the way
        user = UserModel(
            {
                "username": username,
                "email": f"{username}@test.com",
                "password": PASSWORD,
            }
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role_id}).save()
        return user

    def enable_mfa(self, user, backup_codes=2):
        """Simulates a user that enrolled before (MFA_ENABLED=1 or other version)."""
        secret = pyotp.random_base32()
        user.set_totp_secret(secret)
        user.mfa_enabled = True
        user.save()
        codes = [secrets.token_hex(5) for _ in range(backup_codes)]
        for code in codes:
            MFABackupCodeModel({"user_id": user.id, "code": code}).save()
        return secret, codes

    def session_token(self, user):
        # Full session without the login: the current TOTP code is not spent
        return Auth.issue_session_tokens(user)["token"]

    def login(self, username, totp_code=None):
        body = {"username": username, "password": PASSWORD}
        if totp_code is not None:
            body["totp_code"] = totp_code
        return self.client.post(
            LOGIN_URL, data=json.dumps(body), headers=JSON_HEADER
        )

    def setup(self, token):
        return self.client.post(MFA_SETUP_URL, headers=auth_header(token))

    def verify(self, token, body):
        return self.client.post(
            MFA_VERIFY_URL, data=json.dumps(body), headers=auth_header(token)
        )

    def reload(self, user_id):
        db.session.expire_all()
        return UserModel.get_one_user(user_id)

    def backup_code_count(self, user_id):
        return MFABackupCodeModel.query.filter_by(user_id=user_id).count()

    def assert_enrollment_disabled(self, response):
        self.assertEqual(501, response.status_code, response.json)
        self.assertEqual({"error": DISABLED_MESSAGE}, response.json)
        self.assertNotIn("WWW-Authenticate", response.headers)

    def generate_api_key(self, token, body=None):
        return self.client.post(
            API_KEY_URL, data=json.dumps(body or {}), headers=auth_header(token)
        )


# --------------------------------------------------------------------------
# A. Enrollment disabled
# --------------------------------------------------------------------------
class _EnrollmentDisabledCases:
    def test_setup_returns_501(self):
        ana = self.create_user("ana")
        self.assert_enrollment_disabled(self.setup(self.session_token(ana)))
        ana = self.reload(ana.id)
        self.assertIsNone(ana.totp_secret)
        self.assertFalse(ana.mfa_enabled)

    def test_verify_returns_501(self):
        ana = self.create_user("ana")
        response = self.verify(self.session_token(ana), {"totp_code": "123456"})
        self.assert_enrollment_disabled(response)
        self.assertNotIn("token", response.json)
        self.assertFalse(self.reload(ana.id).mfa_enabled)
        self.assertEqual(0, self.backup_code_count(ana.id))

    def test_verify_returns_501_before_validating_the_body(self):
        ana = self.create_user("ana")
        self.assert_enrollment_disabled(self.verify(self.session_token(ana), {}))

    def test_verify_with_started_enrollment_returns_501(self):
        ana = self.create_user("ana")
        token = self.session_token(ana)
        secret = pyotp.random_base32()
        ana.set_totp_secret(secret)
        ana.save()
        response = self.verify(token, {"totp_code": pyotp.TOTP(secret).now()})
        self.assert_enrollment_disabled(response)
        ana = self.reload(ana.id)
        self.assertFalse(ana.mfa_enabled)
        self.assertEqual(secret, ana.get_totp_secret())
        self.assertIsNone(ana.totp_last_counter)
        self.assertEqual(0, self.backup_code_count(ana.id))

    def test_enrollment_token_gets_501(self):
        ana = self.create_user("ana")
        temp = Auth.generate_token(ana.id, purpose=TOKEN_PURPOSE_MFA_SETUP)
        self.assert_enrollment_disabled(self.setup(temp))
        self.assert_enrollment_disabled(self.verify(temp, {"totp_code": "123456"}))

    def test_enrolled_user_gets_501(self):
        ana = self.create_user("ana")
        secret, _ = self.enable_mfa(ana)
        token = self.session_token(ana)
        # 501, not the 400 "already enabled"
        self.assert_enrollment_disabled(self.setup(token))
        self.assert_enrollment_disabled(
            self.verify(token, {"totp_code": pyotp.TOTP(secret).now()})
        )
        ana = self.reload(ana.id)
        self.assertTrue(ana.mfa_enabled)
        self.assertEqual(secret, ana.get_totp_secret())
        self.assertEqual(2, self.backup_code_count(ana.id))

    def test_every_role_gets_501(self):
        for role in ALL_ROLES:
            with self.subTest(role=role):
                user = self.create_user(f"user_{role}", role)
                token = self.session_token(user)
                self.assert_enrollment_disabled(self.setup(token))
                self.assert_enrollment_disabled(
                    self.verify(token, {"totp_code": "123456"})
                )

    def test_authentication_errors_come_first(self):
        ana = self.create_user("ana")
        # No Authorization header
        for method in (
            lambda: self.client.post(MFA_SETUP_URL, headers=JSON_HEADER),
            lambda: self.client.post(
                MFA_VERIFY_URL,
                data=json.dumps({"totp_code": "123456"}),
                headers=JSON_HEADER,
            ),
        ):
            self.assertEqual(400, method().status_code)
        # Token that is not valid
        for response in (
            self.setup("not-a-token"),
            self.verify("not-a-token", {"totp_code": "123456"}),
        ):
            self.assertEqual(401, response.status_code, response.json)
            self.assertIn("WWW-Authenticate", response.headers)
        # Purpose token that is not mfa_setup
        reset = Auth.generate_token(ana.id, purpose=TOKEN_PURPOSE_PWD_RESET)
        for response in (
            self.setup(reset),
            self.verify(reset, {"totp_code": "123456"}),
        ):
            self.assertEqual(403, response.status_code, response.json)
            self.assertEqual("purpose_token", response.json.get("error_code"))
        # API key
        response = self.generate_api_key(self.session_token(ana))
        self.assertEqual(201, response.status_code, response.json)
        api_key = response.json["api_key"]
        for response in (
            self.setup(api_key),
            self.verify(api_key, {"totp_code": "123456"}),
        ):
            self.assertEqual(403, response.status_code, response.json)
            self.assertEqual("api_key_forbidden", response.json.get("error_code"))

    def test_endpoints_stay_documented(self):
        response = self.client.get("/swagger/")
        self.assertEqual(200, response.status_code)
        paths = response.json["paths"]
        self.assertIn("post", paths[PREFIX + "/mfa/setup/"])
        verify = paths[PREFIX + "/mfa/verify/"]
        self.assertIn("post", verify)
        body_params = [p for p in verify["post"]["parameters"] if p["in"] == "body"]
        self.assertEqual(1, len(body_params), verify)
        self.assertEqual(
            "#/definitions/MFAVerifyRequest", body_params[0]["schema"]["$ref"]
        )
        self.assertIn("delete", paths[PREFIX + "/user/{user_id}/mfa/"])

    def test_rejection_is_logged(self):
        ana = self.create_user("ana")
        token = self.session_token(ana)
        with self.assertLogs(current_app.logger, "ERROR") as logs:
            self.setup(token)
        self.assertTrue(
            any("MFA_ENABLED=" in line and "/mfa/setup/" in line for line in logs.output),
            logs.output,
        )


class TestEnrollmentDisabledLevel1(_EnrollmentDisabledCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {}


class TestEnrollmentDisabledLevel2(_EnrollmentDisabledCases, _MfaLevelTestBase):
    security_level = 2
    config_overrides = {}


class TestEnrollmentDisabledLevel3(_EnrollmentDisabledCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = {**LEVEL3_WITHOUT_ENROLLMENT, "DOCS_ENABLED": 1}


class TestEnrollmentNonBinaryValue(_MfaLevelTestBase):
    security_level = 1
    security_environ = {"MFA_ENABLED": "2"}

    def test_value_other_than_one_disables_enrollment(self):
        self.assertEqual(2, current_app.config["MFA_ENABLED"])
        ana = self.create_user("ana")
        self.assert_enrollment_disabled(self.setup(self.session_token(ana)))


# --------------------------------------------------------------------------
# B. Enrollment enabled
# --------------------------------------------------------------------------
class _EnrollmentEnabledCases:
    def enroll(self, ana):
        token = self.session_token(ana)
        response = self.setup(token)
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("secret", response.json)
        self.assertTrue(response.json["provisioning_uri"].startswith("otpauth://totp/"))
        secret = response.json["secret"]
        response = self.verify(token, {"totp_code": pyotp.TOTP(secret).now()})
        self.assertEqual(200, response.status_code, response.json)
        return secret, response

    def test_voluntary_enrollment(self):
        ana = self.create_user("ana")
        secret, response = self.enroll(ana)
        self.assertEqual(ana.id, response.json["id"])
        self.assertIn("token", response.json)
        self.assertEqual(
            current_app.config["MFA_BACKUP_CODES_NUMBER"],
            len(response.json["backup_codes"]),
        )
        self.assertEqual(
            current_app.config["REFRESH_TOKEN_ENABLED"] == 1,
            "refresh_token" in response.json,
        )
        self.assertTrue(self.reload(ana.id).mfa_enabled)

    def test_login_after_voluntary_enrollment(self):
        ana = self.create_user("ana")
        secret, _ = self.enroll(ana)
        response = self.login("ana")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIs(True, response.json["mfa_required"])
        self.assertNotIn("token", response.json)
        # verify does not spend the anti-replay counter
        response = self.login("ana", pyotp.TOTP(secret).now())
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)

    def test_second_setup_is_rejected_as_today(self):
        ana = self.create_user("ana")
        self.enroll(ana)
        response = self.setup(self.session_token(self.reload(ana.id)))
        self.assertEqual(400, response.status_code, response.json)


class TestVoluntaryEnrollmentLevel1(_EnrollmentEnabledCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {"MFA_ENABLED": 1}


class TestVoluntaryEnrollmentLevel2(_EnrollmentEnabledCases, _MfaLevelTestBase):
    security_level = 2
    config_overrides = {"MFA_ENABLED": 1}


class TestVoluntaryEnrollmentLevel3(_EnrollmentEnabledCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = {"MFA_REQUIRED": 0}


# --------------------------------------------------------------------------
# C. Enrollment required during the login
# --------------------------------------------------------------------------
class _RequiredEnrollmentCases:
    def test_enrollment_during_login(self):
        self.create_user("ana")
        response = self.login("ana")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIs(True, response.json["mfa_setup_required"])
        self.assertNotIn("token", response.json)
        temp = response.json["temp_token"]

        response = self.setup(temp)
        self.assertEqual(200, response.status_code, response.json)
        secret = response.json["secret"]
        response = self.verify(temp, {"totp_code": pyotp.TOTP(secret).now()})
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assertTrue(response.json["backup_codes"])

        response = self.login("ana")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIs(True, response.json["mfa_required"])

    def test_enrollment_token_is_limited_to_enrollment(self):
        ana = self.create_user("ana")
        temp = self.login("ana").json["temp_token"]
        response = self.client.get(f"{USER_URL}{ana.id}/", headers=auth_header(temp))
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("purpose_token", response.json.get("error_code"))


class TestRequiredEnrollmentLevel3(_RequiredEnrollmentCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = {}


class TestRequiredEnrollmentLevel1(_RequiredEnrollmentCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {"MFA_ENABLED": 1, "MFA_REQUIRED": 1}


# --------------------------------------------------------------------------
# D. Users that already have MFA with the enrollment disabled
# --------------------------------------------------------------------------
class _EnrolledUserCases:
    def setUp(self):
        super().setUp()
        self.ana = self.create_user("ana")
        self.secret, self.codes = self.enable_mfa(self.ana)

    def test_login_without_code_asks_for_it(self):
        response = self.login("ana")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIs(True, response.json["mfa_required"])
        self.assertNotIn("token", response.json)

    def test_login_with_totp_code(self):
        response = self.login("ana", pyotp.TOTP(self.secret).now())
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)

    def test_login_with_backup_code(self):
        response = self.login("ana", self.codes[0])
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        response = self.login("ana", self.codes[0])
        self.assertEqual(400, response.status_code, response.json)
        self.assertEqual({"error": BAD_TOTP_ERROR}, response.json)
        response = self.login("ana", self.codes[1])
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)

    def test_login_with_wrong_code(self):
        wrong = pyotp.TOTP(self.secret).at(time.time() - 600)
        response = self.login("ana", wrong)
        self.assertEqual(400, response.status_code, response.json)
        self.assertEqual({"error": BAD_TOTP_ERROR}, response.json)

    def test_user_enrolled_while_enabled_keeps_mfa(self):
        beto = self.create_user("beto")
        token = self.session_token(beto)
        current_app.config["MFA_ENABLED"] = 1
        try:
            response = self.setup(token)
            self.assertEqual(200, response.status_code, response.json)
            secret = response.json["secret"]
            response = self.verify(token, {"totp_code": pyotp.TOTP(secret).now()})
            self.assertEqual(200, response.status_code, response.json)
            backup_codes = response.json["backup_codes"]
        finally:
            current_app.config["MFA_ENABLED"] = 0

        response = self.login("beto")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIs(True, response.json["mfa_required"])
        response = self.login("beto", backup_codes[0])
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assert_enrollment_disabled(self.setup(response.json["token"]))


class TestEnrolledUserLevel1(_EnrolledUserCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {}


class TestEnrolledUserLevel2(_EnrolledUserCases, _MfaLevelTestBase):
    security_level = 2
    config_overrides = {}


class TestEnrolledUserLevel3(_EnrolledUserCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = dict(LEVEL3_WITHOUT_ENROLLMENT)


# --------------------------------------------------------------------------
# E. MFA reset with the enrollment disabled
# --------------------------------------------------------------------------
class _MfaResetCases:
    def delete_mfa(self, token, user_id):
        return self.client.delete(
            f"{USER_URL}{user_id}/mfa/", headers=auth_header(token)
        )

    def get_user_info(self, token, user_id):
        return self.client.get(f"{USER_URL}{user_id}/", headers=auth_header(token))

    def test_self_reset(self):
        ana = self.create_user("ana")
        self.enable_mfa(ana)
        token = self.session_token(ana)
        # A single key: no rotation, so no grace window
        response = self.generate_api_key(token)
        self.assertEqual(201, response.status_code, response.json)
        api_key = response.json["api_key"]

        response = self.delete_mfa(token, ana.id)
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual({"message": RESET_MESSAGE}, response.json)
        ana_db = self.reload(ana.id)
        self.assertFalse(ana_db.mfa_enabled)
        self.assertIsNone(ana_db.totp_secret)
        self.assertEqual(0, self.backup_code_count(ana.id))
        self.assertEqual(401, self.get_user_info(token, ana.id).status_code)
        self.assertEqual(401, self.get_user_info(api_key, ana.id).status_code)

        response = self.login("ana")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assertNotIn("mfa_required", response.json)
        self.assertNotIn("mfa_setup_required", response.json)
        self.assert_enrollment_disabled(self.setup(response.json["token"]))

    def test_admin_reset(self):
        for role in (ADMIN_ROLE, PLATFORM_ADMIN_ROLE):
            with self.subTest(role=role):
                actor = self.create_user(f"actor_{role}", role)
                ana = self.create_user(f"ana_{role}")
                self.enable_mfa(ana)
                t_ana = self.session_token(ana)
                response = self.delete_mfa(self.session_token(actor), ana.id)
                self.assertEqual(200, response.status_code, response.json)
                self.assertFalse(self.reload(ana.id).mfa_enabled)
                self.assertEqual(401, self.get_user_info(t_ana, ana.id).status_code)

    def test_reset_revokes_api_key_in_rotation_grace(self):
        for mode in ("self", "admin"):
            with self.subTest(reset_by=mode):
                ana = self.create_user(f"ana_{mode}")
                self.enable_mfa(ana)
                token = self.session_token(ana)
                first = self.generate_api_key(token)
                self.assertEqual(201, first.status_code, first.json)
                second = self.generate_api_key(token)
                self.assertEqual(201, second.status_code, second.json)
                keys = (first.json["api_key"], second.json["api_key"])
                # Default grace window (60 minutes): both keys are valid
                for key in keys:
                    self.assertEqual(200, self.get_user_info(key, ana.id).status_code)
                before = self.reload(ana.id)
                version = before.api_key_version
                self.assertIsNotNone(before.api_key_grace_until)

                actor_token = token
                if mode == "admin":
                    actor_token = self.session_token(
                        self.create_user("cfadmin_r", ADMIN_ROLE)
                    )
                response = self.delete_mfa(actor_token, ana.id)
                self.assertEqual(200, response.status_code, response.json)

                for key in keys:
                    response = self.get_user_info(key, ana.id)
                    self.assertEqual(401, response.status_code, response.json)
                    self.assertIn("WWW-Authenticate", response.headers)
                    self.assertEqual(API_KEY_REVOKED_ERROR, response.json["error"])
                after = self.reload(ana.id)
                self.assertIsNone(after.api_key_previous_version)
                self.assertIsNone(after.api_key_grace_until)
                self.assertIsNone(after.api_key_issued_at)
                self.assertGreater(after.api_key_version, version)

    def test_other_user_can_not_reset(self):
        ana = self.create_user("ana")
        self.enable_mfa(ana)
        beto = self.create_user("beto")
        response = self.delete_mfa(self.session_token(beto), ana.id)
        self.assertEqual(403, response.status_code, response.json)
        self.assertTrue(self.reload(ana.id).mfa_enabled)


class TestMfaResetLevel1(_MfaResetCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {}


class TestMfaResetLevel2(_MfaResetCases, _MfaLevelTestBase):
    security_level = 2
    config_overrides = {}


class TestMfaResetLevel3(_MfaResetCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = dict(LEVEL3_WITHOUT_ENROLLMENT)


# --------------------------------------------------------------------------
# F. New TOTP codes (API keys and platform roles)
# --------------------------------------------------------------------------
class _StepUpBase:
    def grant_platform_role(self, token, user_id, totp_code=None):
        body = {"user_id": user_id, "role_id": PLATFORM_VIEWER_ROLE}
        if totp_code is not None:
            body["totp_code"] = totp_code
        return self.client.post(
            USER_ROLE_URL, data=json.dumps(body), headers=auth_header(token)
        )

    def granted(self, user_id):
        return (
            UserRoleModel.query.filter_by(
                user_id=user_id, role_id=PLATFORM_VIEWER_ROLE
            ).count()
            == 1
        )

    def prepare_platform_grant(self):
        actor = self.create_user("cfplatform", PLATFORM_ADMIN_ROLE)
        actor_secret, _ = self.enable_mfa(actor)
        ana = self.create_user("ana")
        return self.session_token(actor), actor_secret, ana


class _NoStepUpCases(_StepUpBase):
    def test_api_key_without_code(self):
        ana = self.create_user("ana")
        self.enable_mfa(ana)
        response = self.generate_api_key(self.session_token(ana))
        self.assertEqual(201, response.status_code, response.json)
        self.assertIn("api_key", response.json)

    def test_platform_role_without_code(self):
        token, _, ana = self.prepare_platform_grant()
        response = self.grant_platform_role(token, ana.id)
        self.assertIn(response.status_code, (200, 201), response.json)
        self.assertTrue(self.granted(ana.id))


class TestNoStepUpLevel1(_NoStepUpCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {}


class TestNoStepUpLevel2(_NoStepUpCases, _MfaLevelTestBase):
    security_level = 2
    config_overrides = {}


class TestNoStepUpLevel3WithoutEnrollment(_NoStepUpCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = dict(LEVEL3_WITHOUT_ENROLLMENT)


class _StepUpCases(_StepUpBase):
    def test_api_key_requires_code(self):
        ana = self.create_user("ana")
        secret, _ = self.enable_mfa(ana)
        token = self.session_token(ana)
        response = self.generate_api_key(token)
        self.assertEqual(400, response.status_code, response.json)
        self.assertEqual({"error": API_KEY_STEPUP_ERROR}, response.json)
        response = self.generate_api_key(
            token, {"totp_code": pyotp.TOTP(secret).now()}
        )
        self.assertEqual(201, response.status_code, response.json)

    def test_platform_role_requires_code(self):
        token, secret, ana = self.prepare_platform_grant()
        response = self.grant_platform_role(token, ana.id)
        self.assertEqual(400, response.status_code, response.json)
        self.assertEqual({"error": ROLE_STEPUP_ERROR}, response.json)
        self.assertFalse(self.granted(ana.id))
        response = self.grant_platform_role(
            token, ana.id, pyotp.TOTP(secret).now()
        )
        self.assertIn(response.status_code, (200, 201), response.json)
        self.assertTrue(self.granted(ana.id))

    def test_user_without_mfa_needs_no_code(self):
        beto = self.create_user("beto")
        response = self.generate_api_key(self.session_token(beto))
        self.assertEqual(201, response.status_code, response.json)


class TestStepUpLevel3(_StepUpCases, _MfaLevelTestBase):
    security_level = 3
    config_overrides = {}


class TestStepUpLevel1Enabled(_StepUpCases, _MfaLevelTestBase):
    security_level = 1
    config_overrides = {
        "MFA_ENABLED": 1,
        "API_KEY_STEPUP_TOTP": 1,
        "PLATFORM_ROLE_STEPUP_TOTP": 1,
    }


# --------------------------------------------------------------------------
# G. Value by level (no application)
# --------------------------------------------------------------------------
class TestMfaEnabledByLevel(unittest.TestCase):
    def test_default_by_level(self):
        for level, expected in ((1, 0), (2, 0), (3, 1)):
            with self.subTest(level=level):
                self.assertEqual(
                    expected, build_security_level_config(level).MFA_ENABLED
                )

    def test_variable_overrides_level(self):
        self.assertEqual(
            1, build_security_level_config(1, environ={"MFA_ENABLED": "1"}).MFA_ENABLED
        )
        config = build_security_level_config(
            3,
            environ={
                "MFA_ENABLED": "0",
                "MFA_REQUIRED": "0",
                "API_KEY_STEPUP_TOTP": "0",
                "PLATFORM_ROLE_STEPUP_TOTP": "0",
            },
        )
        self.assertEqual(0, config.MFA_ENABLED)


if __name__ == "__main__":
    unittest.main()
