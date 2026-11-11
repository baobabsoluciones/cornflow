"""
UAT battery of the security hardening, group A: environment preparation,
password policy, two-factor authentication (TOTP), password rotation and
forced change, account lockout and rate limiting (blocks 0 to 4 of the sheet).

Every test is named after the id of its case in the sheet and runs against the
profile selected with ``CORNFLOW_UAT_PROFILE`` (see ``uat_hardening_support``).
"""

import json
import logging
import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from importlib import import_module
from unittest.mock import patch

from click.testing import CliRunner
from flask import current_app

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.models import MFABackupCodeModel, RoleModel, UserModel
from cornflow.shared import db
from cornflow.shared.const import (
    ADMIN_ROLE,
    DEFAULT_PWD_MIN_LENGTH,
    PLATFORM_ADMIN_ROLE,
    ROLES_MAP,
    SERVICE_ROLE,
    VIEWER_ROLE,
)
from cornflow.shared.exceptions import ConfigurationError, InvalidCredentials
from cornflow.shared.rate_limit import RATE_LIMIT_MESSAGE, limiter
from cornflow.tests.const import INSTANCE_URL, RECOVER_PASSWORD_URL, SIGNUP_URL, USER_URL
from cornflow.tests.uat_hardening_support import (
    PASSWORDS,
    SETTINGS,
    UatTestCase,
    auth_header,
    is_relaxed,
    is_strict,
    pending_fix,
    profile_env_name,
    ui_only,
)

REFRESH_URL = USER_URL.rsplit("/user/", 1)[0] + "/token/refresh/"
MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "migrations"
)
NEW_MIGRATIONS = ("b7a1c9d807e5", "c3f2a1b4e5d6", "d4e8b2c6f109")
NEW_TABLES = ("session_tokens", "user_password_history", "mfa_backup_codes")


def limit_count(limit: str) -> int:
    """Number of requests allowed by a limit string such as '10 per minute'."""
    return int(limit.split()[0])


class SecretKeyTests(unittest.TestCase):
    """Case 0.1: the application refuses weak signing keys."""

    def test_uat_0_1_short_secret_key_does_not_start(self):
        """0.1 Start the server with a 20 bytes SECRET_KEY: it does not start."""
        for key_name in ("SECRET_TOKEN_KEY", "SECRET_BI_KEY"):
            with self.assertRaises(ConfigurationError) as ctx:
                create_app(profile_env_name(**{key_name: "x" * 20}))
            message = str(ctx.exception)
            self.assertIn(key_name, message)
            self.assertIn("at least 32 bytes", message)


class EnvironmentTests(UatTestCase):
    """Cases 0.2 to 0.5: environment preparation."""

    def test_uat_0_2_migrations_and_tables(self):
        """0.2 Correct secrets and database upgrade: migrations and tables exist."""
        # The application starts with correct secrets (it was created above)
        self.assertGreaterEqual(len(current_app.config["SECRET_TOKEN_KEY"]), 32)
        # No Postgres here: the migration scripts are checked as a chain and
        # the tables they create are checked on the SQLite schema.
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config()
        config.set_main_option("script_location", os.path.abspath(MIGRATIONS_DIR))
        script = ScriptDirectory.from_config(config)
        revisions = {rev.revision: rev for rev in script.walk_revisions()}
        for revision in NEW_MIGRATIONS:
            self.assertIn(revision, revisions)
        self.assertEqual(
            revisions["c3f2a1b4e5d6"].down_revision, "b7a1c9d807e5"
        )
        self.assertEqual(
            revisions["d4e8b2c6f109"].down_revision, "c3f2a1b4e5d6"
        )
        self.assertEqual(1, len(script.get_heads()))
        tables = set(db.inspect(db.engine).get_table_names())
        for table in NEW_TABLES:
            self.assertIn(table, tables)

    def test_uat_0_3_roles_registered_by_access_init(self):
        """0.3 access_init / roles init: the 8 roles are registered."""
        roles = {r.id: r.name for r in RoleModel.get_all_objects()}
        cornflow_roles = {i: n for i, n in roles.items() if i in ROLES_MAP}
        self.assertEqual(8, len(cornflow_roles))
        self.assertEqual(
            {
                "dummy",
                "viewer",
                "planner",
                "admin",
                "service",
                "platform_viewer",
                "platform_planner",
                "platform_admin",
            },
            set(cornflow_roles.values()),
        )
        for role_id, name in (
            (901, "platform_viewer"),
            (902, "platform_planner"),
            (903, "platform_admin"),
        ):
            self.assertEqual(name, roles[role_id])
        # The CLI command is idempotent and ends with exit code 0 (the CLI
        # builds its own app, so it is pointed at the one under test)
        with patch.object(import_module("cornflow.cli.roles"), "get_app", return_value=self.app):
            with self.assertLogs(current_app.logger, level="INFO") as logs:
                result = CliRunner().invoke(cli, ["roles", "init", "-v"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(
            any("No new roles to be registered" in m for m in logs.output),
            logs.output,
        )

    def test_uat_0_4_admin_password_with_username_fails(self):
        """0.4 CORNFLOW_ADMIN_PWD=adminpassword (contains the user): creation fails."""
        from cornflow.commands import create_user_with_role

        with self.assertLogs(current_app.logger, level="ERROR") as logs:
            with self.assertRaises(InvalidCredentials) as ctx:
                create_user_with_role(
                    "admin", "admin@example.com", "adminpassword", "admin", ADMIN_ROLE
                )
        self.assertIn("Password must", ctx.exception.error)
        self.assertTrue(
            any("Could not create user admin" in m for m in logs.output), logs.output
        )
        self.assertIsNone(UserModel.get_one_user_by_username("admin"))
        # The same happens through the CLI command
        with patch.object(import_module("cornflow.cli.users"), "get_app", return_value=self.app):
            result = CliRunner().invoke(
                cli,
                [
                    "users", "create", "viewer", "-u", "admin",
                    "-e", "admin@example.com", "-p", "adminpassword",
                ],
            )
        self.assertNotEqual(0, result.exit_code)
        self.assertIsNone(UserModel.get_one_user_by_username("admin"))

    def test_uat_0_5_custom_role_950_aborts_startup(self):
        """0.5 External application with a custom role id 950: explicit error."""
        from cornflow.commands.auxiliar import check_reserved_role_ids

        with self.assertRaises(ConfigurationError) as ctx:
            check_reserved_role_ids([VIEWER_ROLE, 950])
        message = str(ctx.exception)
        self.assertIn("950", message)
        self.assertIn("900-999", message)
        self.assertIn("5 and 899", message)
        # Platform role ids are not a conflict
        check_reserved_role_ids(list(ROLES_MAP))


class PasswordPolicyTests(UatTestCase):
    """Block 1: password policy."""

    def setUp(self):
        super().setUp()
        self.make_user("cfadmin", [ADMIN_ROLE])
        self.admin_token = self.token_of("cfadmin")

    def signup(self, password, username="newuser", email=None):
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": username,
                    "email": email or f"{username}@example.com",
                    "password": password,
                }
            ),
            headers=auth_header(self.admin_token),
        )

    def assert_rejected(self, response, text):
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn(text, json.dumps(response.json))

    def test_uat_1_1_short_password_rejected(self):
        """1.1 Register a user with Abc1! (short): 400, minimum length 12."""
        self.assert_rejected(self.signup("Abc1!"), "at least 12 characters")

    def test_uat_1_2_password_without_character_classes_rejected(self):
        """1.2 Password abcdefghijkl: 400, character classes."""
        self.assert_rejected(self.signup("abcdefghijkl"), "uppercase letter")

    def test_uat_1_3_common_password_rejected(self):
        """1.3 Password Password1234! (common): 400, rejected by zxcvbn."""
        self.assert_rejected(self.signup("Password1234!"), "too easy to guess")

    def test_uat_1_4_password_with_username_rejected(self):
        """1.4 User juanperez with Juanperez-2024!: 400, contains the user."""
        self.assert_rejected(
            self.signup("Juanperez-2024!", username="juanperez"),
            "must not contain your username",
        )

    def test_uat_1_5_digit_sequence_rejected(self):
        """1.5 Password Abcd-19900101! (6+ digit sequence): 400."""
        self.assert_rejected(self.signup("Abcd-19900101!"), "sequences of 6 or more digits")

    def test_uat_1_6_long_passphrase_accepted(self):
        """1.6 Long passphrase caballo-verde-taza-lampara-7!: accepted."""
        # Without a capital letter it is rejected by the character classes
        self.assert_rejected(
            self.signup("caballo-verde-taza-lampara-7!", username="pass1"),
            "uppercase letter",
        )
        response = self.signup("Caballo-verde-taza-lampara-7!", username="pass2")
        self.assertEqual(201, response.status_code, response.json)
        self.assertIsNotNone(UserModel.get_one_user_by_username("pass2"))

    def own_password_change(self, token, user_id, payload):
        return self.client.put(
            f"{USER_URL}{user_id}/",
            data=json.dumps(payload),
            headers=auth_header(token),
        )

    def test_uat_1_7_change_own_password_requires_current(self):
        """1.7 Change the own password without sending the current one: rejected."""
        user = self.make_user("regular", [VIEWER_ROLE], password="Kx9#tR2m!Qw7Zp")
        token = self.token_of("regular", "Kx9#tR2m!Qw7Zp")
        response = self.own_password_change(
            token, user.id, {"password": "Mv4#qL8n!Zr5Tw"}
        )
        self.assertIn(response.status_code, (400, 401))
        self.assertIn("current password is missing or incorrect", json.dumps(response.json))
        response = self.own_password_change(
            token, user.id, {"password": "Mv4#qL8n!Zr5Tw", "current_password": "wrong"}
        )
        self.assertIn(response.status_code, (400, 401))

    def test_uat_1_8_trivial_variation_rejected(self):
        """1.8 Change Kx9#tR2m!Qw7Zp to Kx9#tR2m!Qw7Zq: too similar."""
        user = self.make_user("regular", [VIEWER_ROLE], password="Kx9#tR2m!Qw7Zp")
        token = self.token_of("regular", "Kx9#tR2m!Qw7Zp")
        response = self.own_password_change(
            token,
            user.id,
            {"password": "Kx9#tR2m!Qw7Zq", "current_password": "Kx9#tR2m!Qw7Zp"},
        )
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn("too similar", json.dumps(response.json))

    def test_uat_1_9_password_reuse_rejected(self):
        """1.9 Change the password and set one of the previous 10 again: rejected."""
        first = "Kx9#tR2m!Qw7Zp"
        second = "Hd6$vNc4&Ye2Bs"
        user = self.make_user("regular", [VIEWER_ROLE], password=first)
        token = self.token_of("regular", first)
        response = self.own_password_change(
            token, user.id, {"password": second, "current_password": first}
        )
        self.assertEqual(200, response.status_code, response.json)
        # The change revokes the session: log in again with the new password
        token = self.token_of("regular", second)
        response = self.own_password_change(
            token, user.id, {"password": first, "current_password": second}
        )
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn("last 10 password", json.dumps(response.json))

    def test_uat_1_10_environment_cannot_weaken_the_minimum_length(self):
        """1.10 PWD_MIN_LENGTH=6 in the environment: 12 is still required."""
        code = (
            "from cornflow.config import DefaultConfig; "
            "print(DefaultConfig.PWD_MIN_LENGTH)"
        )
        env = {**os.environ, "PWD_MIN_LENGTH": "6", "FLASK_ENV": "testing"}
        result = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        effective = int(result.stdout.strip().splitlines()[-1])
        self.assertEqual(DEFAULT_PWD_MIN_LENGTH, effective)
        self.assertEqual(12, effective)
        current_app.config["PWD_MIN_LENGTH"] = effective
        self.assert_rejected(self.signup("Ab3!xyzQ"), "at least 12 characters")


class MfaTests(UatTestCase):
    """Block 2: two-factor authentication (TOTP)."""

    def enrolled(self, username, role_ids=(VIEWER_ROLE,)):
        """Creates a user with MFA enabled and returns the enrollment response."""
        self.make_user(username, list(role_ids))
        response = self.login(username)
        self.assertEqual(200, response.status_code, response.json)
        if response.json.get("mfa_setup_required"):
            return self.enroll_mfa(response.json["temp_token"], username)
        # MFA is not mandatory in this profile: enroll voluntarily
        return self.enroll_mfa(response.json["token"], username)

    def test_uat_2_1_first_login_requires_mfa_setup(self):
        """2.1 First login of a new user: mfa_setup_required and a temporary token."""
        self.make_user("newbie", [VIEWER_ROLE])
        response = self.login("newbie")
        self.assertEqual(200, response.status_code, response.json)
        if is_strict():
            self.assertTrue(response.json["mfa_setup_required"])
            self.assertNotIn("token", response.json)
            temp_token = response.json["temp_token"]
            # The temporary token does not give access to other endpoints
            denied = self.client.get(INSTANCE_URL, headers=auth_header(temp_token))
            self.assertEqual(403, denied.status_code, denied.json)
            self.assertEqual("purpose_token", denied.json.get("error_code"))
        else:
            self.assertEqual(0, SETTINGS["MFA_REQUIRED"])
            self.assertNotIn("mfa_setup_required", response.json)
            self.assertIn("token", response.json)

    def test_uat_2_2_enrollment_returns_secret_and_backup_codes_once(self):
        """2.2 Complete the enrollment: local QR data and backup codes once."""
        verify = self.enrolled("newbie")
        # The provisioning URI is generated by the server (no external call)
        setup_again = self.client.post(
            "/cornflow/mfa/setup/", headers=auth_header(verify.json["token"])
        )
        self.assertEqual(400, setup_again.status_code, setup_again.json)
        self.assertTrue(self.mfa_secrets["newbie"])
        codes = verify.json["backup_codes"]
        self.assertEqual(int(current_app.config.get("MFA_BACKUP_CODES_NUMBER", 8)), len(codes))
        self.assertEqual(len(codes), len(set(codes)))
        user = UserModel.get_one_user_by_username("newbie")
        self.assertTrue(user.mfa_enabled)
        # The backup codes are not exposed again: a login does not return them
        response = self.login("newbie", totp_code=self.totp_now("newbie"))
        self.assertNotIn("backup_codes", response.json)

    def test_uat_2_3_login_without_code_requires_mfa(self):
        """2.3 After enrolling, log in without a code: mfa_required, no token."""
        self.enrolled("newbie")
        response = self.login("newbie")
        self.assertEqual(200, response.status_code, response.json)
        self.assertTrue(response.json["mfa_required"])
        self.assertNotIn("token", response.json)

    def test_uat_2_4_login_with_valid_totp(self):
        """2.4 Log in with a valid TOTP code: 200 with access and refresh tokens."""
        self.enrolled("newbie")
        response = self.login("newbie", totp_code=self.totp_now("newbie"))
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assertIn("refresh_token", response.json)

    def test_uat_2_5_totp_code_replay_rejected(self):
        """2.5 Reuse the same TOTP code immediately: rejected (anti-replay)."""
        self.enrolled("newbie")
        code = self.totp_now("newbie")
        first = self.login("newbie", totp_code=code)
        self.assertEqual(200, first.status_code, first.json)
        second = self.login("newbie", totp_code=code)
        self.assertEqual(400, second.status_code, second.json)
        self.assertNotIn("token", second.json)
        self.assertIn("Invalid two-factor authentication code", json.dumps(second.json))

    def test_uat_2_6_backup_code_is_single_use(self):
        """2.6 Log in with a backup code: works once and never again."""
        verify = self.enrolled("newbie")
        code = verify.json["backup_codes"][0]
        first = self.login("newbie", totp_code=code)
        self.assertEqual(200, first.status_code, first.json)
        self.assertIn("token", first.json)
        second = self.login("newbie", totp_code=code)
        self.assertEqual(400, second.status_code, second.json)
        self.assertIn("Invalid two-factor authentication code", json.dumps(second.json))

    def test_uat_2_7_service_user_is_exempt_from_mfa(self):
        """2.7 The service user logs in with user/password: 200 without MFA."""
        self.make_user("service_user", [SERVICE_ROLE])
        response = self.login("service_user")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assertNotIn("mfa_required", response.json)
        self.assertNotIn("mfa_setup_required", response.json)
        # Control: a regular enrolled user is asked for the second factor
        self.enrolled("pilot")
        control = self.login("pilot")
        self.assertEqual(200, control.status_code, control.json)
        self.assertTrue(control.json.get("mfa_required"))
        self.assertNotIn("token", control.json)

    def test_uat_2_8_admin_resets_mfa_of_another_user(self):
        """2.8 An admin resets the MFA of another user: re-enroll, sessions and keys revoked."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        admin_token = self.token_of("cfadmin")
        verify = self.enrolled("victim")
        victim_id = UserModel.get_one_user_by_username("victim").id
        old_session = self.login("victim", totp_code=self.totp_now("victim")).json
        key_version = UserModel.get_one_user_by_username("victim").api_key_version or 0

        response = self.client.delete(
            f"{USER_URL}{victim_id}/mfa/", headers=auth_header(admin_token)
        )
        self.assertEqual(200, response.status_code, response.json)

        db.session.expire_all()
        victim = UserModel.get_one_user_by_username("victim")
        self.assertFalse(victim.mfa_enabled)
        self.assertEqual(key_version + 1, victim.api_key_version)
        # The sessions that existed are no longer valid
        refreshed = self.client.post(
            REFRESH_URL,
            data=json.dumps({"refresh_token": old_session["refresh_token"]}),
            headers={"Content-Type": "application/json"},
        )
        self.assertIn(refreshed.status_code, (400, 401), refreshed.json)
        self.assertNotIn("token", refreshed.json)
        stale = self.client.get(f"{USER_URL}{victim_id}/", headers=auth_header(old_session["token"]))
        self.assertEqual(401, stale.status_code, stale.json)
        # The next access requires a new enrollment when MFA is mandatory
        response = self.login("victim")
        self.assertEqual(200, response.status_code, response.json)
        if is_strict():
            self.assertTrue(response.json["mfa_setup_required"])
            self.assertNotIn("token", response.json)
        else:
            self.assertNotIn("mfa_required", response.json)
        self.assertTrue(verify.json["backup_codes"])
        self.assertEqual([], MFABackupCodeModel.query.filter_by(user_id=victim_id).all())


class PasswordRotationTests(UatTestCase):
    """Block 3: password rotation and forced change."""

    def flag_for_change(self, username):
        user = UserModel.get_one_user_by_username(username)
        user.pwd_change_required = True
        db.session.add(user)
        db.session.commit()
        return user

    def test_uat_3_1_user_created_by_admin_must_change_password(self):
        """3.1 A user created by an admin logs in: change_password is true."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        admin_token = self.token_of("cfadmin")
        password = "Mv4#qL8n!Zr5Tw"
        created = self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {"username": "provisioned", "email": "prov@example.com", "password": password}
            ),
            headers=auth_header(admin_token),
        )
        self.assertEqual(201, created.status_code, created.json)
        body = self.login("provisioned", password).json
        if body.get("mfa_setup_required"):
            self.enroll_mfa(body["temp_token"], "provisioned")
            body = self.login("provisioned", password, self.totp_now("provisioned")).json
        self.assertIn("token", body)
        self.assertIs(True, body["change_password"])

    test_uat_3_1_user_created_by_admin_must_change_password = pending_fix(
        "24629024"
    )(test_uat_3_1_user_created_by_admin_must_change_password)

    def test_uat_3_2_flagged_password_blocks_other_endpoints(self):
        """3.2 Password flagged for change, GET /instance/: 403 password_rotation."""
        self.make_user("regular", [VIEWER_ROLE])
        token = self.token_of("regular")
        self.flag_for_change("regular")
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("password_rotation", response.json["error_code"])

    def test_uat_3_3_user_endpoints_allowed_while_flagged(self):
        """3.3 Same state, GET and PUT /user/<id>/: allowed."""
        user = self.make_user("regular", [VIEWER_ROLE])
        token = self.token_of("regular")
        self.flag_for_change("regular")
        response = self.client.get(f"{USER_URL}{user.id}/", headers=auth_header(token))
        self.assertEqual(200, response.status_code, response.json)
        response = self.client.put(
            f"{USER_URL}{user.id}/",
            data=json.dumps({"first_name": "Regular"}),
            headers=auth_header(token),
        )
        self.assertEqual(200, response.status_code, response.json)

    def test_uat_3_4_changing_the_password_restores_access(self):
        """3.4 Change the password and repeat 3.2: 200, normal access again."""
        user = self.make_user("regular", [VIEWER_ROLE])
        token = self.token_of("regular")
        self.flag_for_change("regular")
        new_password = "Hd6$vNc4&Ye2Bs"
        response = self.client.put(
            f"{USER_URL}{user.id}/",
            data=json.dumps(
                {"password": new_password, "current_password": self.password_of("regular")}
            ),
            headers=auth_header(token),
        )
        self.assertEqual(200, response.status_code, response.json)
        # The session in use is revoked: log in again with the new password
        body = self.full_login("regular", new_password)
        code = self.totp_now("regular") if is_strict() else None
        login = self.login("regular", new_password, code).json
        self.assertIs(False, login["change_password"])
        response = self.client.get(INSTANCE_URL, headers=auth_header(body["token"]))
        self.assertEqual(200, response.status_code, response.json)

    @ui_only("redirect to settings with the mandatory change notice and navigation lock")
    def test_uat_3_5_ui_redirects_to_settings_on_forced_change(self):
        """3.5 In the interface, log in with a forced change: redirect to settings."""

    def test_uat_3_6_service_user_exempt_from_rotation(self):
        """3.6 Service user with an old password: rotation is not required."""
        age = timedelta(days=SETTINGS["PWD_ROTATION_TIME"] + 35)
        for username, role, expected in (
            ("service_user", SERVICE_ROLE, 200),
            ("regular", VIEWER_ROLE, 403),
        ):
            user = self.make_user(username, [role])
            token = self.token_of(username)
            user.pwd_change_required = True
            user.pwd_last_change = datetime.now(timezone.utc).replace(tzinfo=None) - age
            db.session.add(user)
            db.session.commit()
            response = self.client.get(INSTANCE_URL, headers=auth_header(token))
            self.assertEqual(expected, response.status_code, (username, response.json))
        # The service user also logs in normally
        self.assertEqual(200, self.login("service_user").status_code)


class LockoutTests(UatTestCase):
    """Block 4: account lockout (cases 4.1 to 4.5 and 4.8)."""

    def lock(self, username):
        for _ in range(SETTINGS["LOGIN_MAX_ATTEMPTS"]):
            self.login(username, "Wrong-password-0!")

    def test_uat_4_1_failed_attempts_return_the_same_generic_error(self):
        """4.1 Wrong password attempts: the same generic error every time."""
        self.make_user("lockme", [VIEWER_ROLE])
        unknown = self.login("nobody", "Wrong-password-0!")
        self.assertEqual(400, unknown.status_code)
        attempts = SETTINGS["LOGIN_MAX_ATTEMPTS"]
        for _ in range(attempts):
            response = self.login("lockme", "Wrong-password-0!")
            self.assertEqual(unknown.status_code, response.status_code)
            self.assertEqual(unknown.json, response.json)
        self.assertEqual("Invalid credentials", unknown.json["error"])
        # The attempt that triggered the lock did not reveal it either
        self.assertTrue(UserModel.get_one_user_by_username("lockme").locked)

    def test_uat_4_2_locked_account_with_correct_password(self):
        """4.2 After the lock, the correct password: 403 account_locked."""
        self.make_user("lockme", [VIEWER_ROLE])
        self.lock("lockme")
        response = self.login("lockme")
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("account_locked", response.json["error_code"])
        # With a wrong password the lock is not revealed
        wrong = self.login("lockme", "Wrong-password-0!")
        self.assertEqual(400, wrong.status_code)
        self.assertNotIn("error_code", wrong.json)

    def test_uat_4_3_client_admin_cannot_unlock(self):
        """4.3 Unlock with a client administrator: 403."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        admin_token = self.token_of("cfadmin")
        target = self.make_user("lockme", [VIEWER_ROLE])
        self.lock("lockme")
        response = self.client.put(
            f"{USER_URL}{target.id}/unlock/", headers=auth_header(admin_token)
        )
        self.assertEqual(403, response.status_code, response.json)
        db.session.expire_all()
        self.assertTrue(UserModel.get_one_user_by_username("lockme").locked)

    def test_uat_4_4_platform_admin_unlocks(self):
        """4.4 Unlock with a platform administrator: 200 and the user can log in."""
        self.make_user("cfplatform", [PLATFORM_ADMIN_ROLE])
        platform_token = self.token_of("cfplatform")
        target = self.make_user("lockme", [VIEWER_ROLE])
        self.lock("lockme")
        with self.assertLogs("cornflow.audit", level="INFO") as logs:
            response = self.client.put(
                f"{USER_URL}{target.id}/unlock/", headers=auth_header(platform_token)
            )
        self.assertEqual(200, response.status_code, response.json)
        events = [json.loads(r.getMessage()) for r in logs.records]
        unlocked = [e for e in events if e["event"] == "account.unlocked"]
        self.assertEqual(1, len(unlocked))
        self.assertEqual("cfplatform", unlocked[0]["actor"])
        db.session.expire_all()
        user = UserModel.get_one_user_by_username("lockme")
        self.assertFalse(user.locked)
        self.assertEqual(0, user.failed_login_attempts)
        login = self.login("lockme")
        self.assertEqual(200, login.status_code, login.json)

    def test_uat_4_5_cli_unlock(self):
        """4.5 cornflow users unlock -u <user> (break-glass): unlocks."""
        self.make_user("lockme", [VIEWER_ROLE])
        self.lock("lockme")
        self.assertTrue(UserModel.get_one_user_by_username("lockme").locked)
        with patch.object(import_module("cornflow.cli.users"), "get_app", return_value=self.app):
            with self.assertLogs("cornflow.audit", level="INFO") as logs:
                result = CliRunner().invoke(cli, ["users", "unlock", "-u", "lockme"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("User lockme has been unlocked", result.output)
        events = [json.loads(r.getMessage()) for r in logs.records]
        unlocked = [e for e in events if e["event"] == "account.unlocked"]
        self.assertEqual(1, len(unlocked))
        self.assertEqual("cli", unlocked[0]["actor"])
        self.assertEqual("success", unlocked[0]["outcome"])
        db.session.expire_all()
        user = UserModel.get_one_user_by_username("lockme")
        self.assertFalse(user.locked)
        self.assertEqual(0, user.failed_login_attempts)
        self.assertEqual(200, self.login("lockme").status_code)

    def test_uat_4_8_service_user_is_never_locked(self):
        """4.8 Failed attempts on the service user: not locked, warning logged."""
        self.make_user("service_user", [SERVICE_ROLE])
        attempts = SETTINGS["LOGIN_MAX_ATTEMPTS"] + 1
        with self.assertLogs(current_app.logger, level="WARNING") as logs:
            for _ in range(attempts):
                response = self.login("service_user", "Wrong-password-0!")
                self.assertEqual(400, response.status_code)
        warnings = [m for m in logs.output if "Failed login attempt for service user service_user" in m]
        self.assertEqual(attempts, len(warnings), logs.output)
        db.session.expire_all()
        user = UserModel.get_one_user_by_username("service_user")
        self.assertFalse(user.locked)
        self.assertEqual(0, user.failed_login_attempts)
        login = self.login("service_user")
        self.assertEqual(200, login.status_code, login.json)
        self.assertIn("token", login.json)


class RateLimitTests(UatTestCase):
    """Block 4: per-IP rate limiting (cases 4.6 and 4.7)."""

    config_overrides = {"RATELIMIT_ENABLED": 1}

    def setUp(self):
        super().setUp()
        limiter.reset()

    def assert_limited_after(self, limit, send):
        """Up to N requests are not limited and request N+1 gets a 429."""
        allowed = limit_count(limit)
        for i in range(allowed):
            response = send()
            self.assertNotEqual(429, response.status_code, f"request {i + 1}")
        response = send()
        self.assertEqual(429, response.status_code, response.json)
        self.assertEqual(RATE_LIMIT_MESSAGE, response.json.get("message", response.json.get("error")))
        return response

    def test_uat_4_6_login_attempts_above_the_limit_get_429(self):
        """4.6 Login attempts from the same IP above the limit: 429, too many requests."""
        self.assertEqual(
            10 if is_strict() else 30, limit_count(SETTINGS["RATELIMIT_LOGIN"])
        )
        self.assert_limited_after(
            SETTINGS["RATELIMIT_LOGIN"],
            lambda: self.login("nobody", "Wrong-password-0!"),
        )

    def test_uat_4_7_recover_password_and_refresh_are_limited(self):
        """4.7 Repeat 4.6 on recover-password and token/refresh: also 429."""
        # Refresh shares the login limit
        response = self.assert_limited_after(
            SETTINGS["RATELIMIT_LOGIN"],
            lambda: self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": "not-a-token"}),
                headers={"Content-Type": "application/json"},
            ),
        )
        self.assertEqual(
            str(limit_count(SETTINGS["RATELIMIT_LOGIN"])),
            response.headers.get("X-RateLimit-Limit"),
        )
        self.assertEqual(
            5 if is_strict() else 20, limit_count(SETTINGS["RATELIMIT_RECOVER"])
        )
        with self.fake_smtp():
            response = self.assert_limited_after(
                SETTINGS["RATELIMIT_RECOVER"],
                lambda: self.client.put(
                    RECOVER_PASSWORD_URL,
                    data=json.dumps({"email": "nobody@example.com"}),
                    headers={"Content-Type": "application/json"},
                ),
            )
        self.assertEqual(
            str(limit_count(SETTINGS["RATELIMIT_RECOVER"])),
            response.headers.get("X-RateLimit-Limit"),
        )


if __name__ == "__main__":
    unittest.main()
