"""
UAT battery of the security hardening, group A: environment preparation,
password policy, two-factor authentication (TOTP), password rotation and
forced change, account lockout and rate limiting (blocks 0 to 4 of the sheet).

Every test is named after the id of its case in the sheet and checks what the
case means at the security level selected with ``CORNFLOW_SECURITY_LEVEL`` (see
``uat_hardening_support``).
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
from cornflow.models import (
    MFABackupCodeModel,
    RoleModel,
    UserModel,
    UserPasswordHistoryModel,
)
from cornflow.shared import db
from cornflow.shared.const import MFA_ENROLLMENT_DISABLED_MESSAGE
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_VIEWER_ROLE,
    ROLES_MAP,
    SERVICE_ROLE,
    VIEWER_ROLE,
)
from cornflow.shared.exceptions import ConfigurationError, InvalidCredentials
from cornflow.shared.security_levels import (
    SECURITY_LEVEL_ENV_VAR,
    SETTINGS_BY_ENV_VAR,
)
from cornflow.shared.rate_limit import RATE_LIMIT_MESSAGE, limiter
from cornflow.tests.uat_hardening_support import MFA_SETUP_URL
from cornflow.tests.const import INSTANCE_URL, RECOVER_PASSWORD_URL, SIGNUP_URL, USER_URL
from cornflow.tests.uat_hardening_support import (
    LEVEL,
    LOCKOUT_OVERRIDES,
    MFA_ENROLLMENT_OVERRIDES,
    PASSWORDS,
    ROTATION_OVERRIDES,
    SIGNUP_ADMIN,
    UatTestCase,
    at_least,
    auth_header,
    by_level,
    ui_only,
    uat_env_name,
)

REFRESH_URL = USER_URL.rsplit("/user/", 1)[0] + "/token/refresh/"
API_KEY_URL = USER_URL + "api-key/"
API_KEY_REVOKED_MESSAGE = "The API key has been revoked, please generate a new one"
MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "migrations"
)
NEW_MIGRATIONS = ("b7a1c9d807e5", "c3f2a1b4e5d6", "d4e8b2c6f109")
NEW_TABLES = ("session_tokens", "user_password_history", "mfa_backup_codes")


def limit_count(limit: str) -> int:
    """Number of requests allowed by a limit string such as '10 per minute'."""
    return int(limit.split()[0])


class SecretKeyTests(unittest.TestCase):
    """Case 0.1: the application refuses weak keys from level 2 on."""

    def test_uat_0_1_short_secret_key_does_not_start(self):
        """0.1 Start with 20-byte keys: level 1 warns, levels 2 and 3 do not start."""
        scenarios = (
            ("FERNET_KEY", {"FERNET_KEY": "x" * 20, "SECRET_BI_KEY": "b" * 40}, "x" * 20),
            ("SECRET_BI_KEY", {"FERNET_KEY": "f" * 40, "SECRET_BI_KEY": "y" * 20}, "y" * 20),
        )
        for key_name, key_environ, short_value in scenarios:
            with self.subTest(key=key_name):
                name = uat_env_name(key_environ=key_environ)
                if LEVEL == 1:
                    with self.assertLogs("cornflow.app", "WARNING") as logs:
                        create_app(name)
                    message = "\n".join(logs.output)
                    self.assertIn(f"{key_name} is shorter than 32 bytes", message)
                else:
                    with self.assertRaises(ConfigurationError) as ctx:
                        create_app(name)
                    message = str(ctx.exception)
                    if key_name == "FERNET_KEY":
                        self.assertIn(
                            f"Security level {LEVEL} requires a secret key of at least 32 bytes",
                            message,
                        )
                        self.assertIn("FERNET_KEY", message)
                    else:
                        self.assertIn(
                            f"Security level {LEVEL} requires SECRET_BI_KEY to be at least 32 bytes",
                            message,
                        )
                self.assertNotIn(short_value, message)


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
        """0.4 CORNFLOW_ADMIN_PWD=adminpassword (weak password): creation fails at every level."""
        from cornflow.commands import create_user_with_role

        with self.assertLogs(current_app.logger, level="ERROR") as logs:
            with self.assertRaises(InvalidCredentials) as ctx:
                create_user_with_role(
                    "admin", "admin@example.com", "adminpassword", "admin", ADMIN_ROLE
                )
        self.assertEqual(
            by_level(
                "Password must contain uppercase and lowercase letters.",
                "Password must contain at least one uppercase letter.",
                "Password must contain at least one uppercase letter.",
            ),
            ctx.exception.error,
        )
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
        self.make_user("cfplatform", [PLATFORM_ADMIN_ROLE])
        self.admin_token = self.token_of(SIGNUP_ADMIN)

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
        """1.1 Register a user with Abc1! (short): 201 at level 1, 400 (minimum 12) from level 2."""
        response = self.signup("Abc1!")
        if LEVEL == 1:
            self.assertEqual(201, response.status_code, response.json)
            self.assertIsNotNone(UserModel.get_one_user_by_username("newuser"))
        else:
            self.assert_rejected(response, "at least 12 characters")

    def test_uat_1_2_password_without_character_classes_rejected(self):
        """1.2 Password abcdefghijkl: 400, character classes."""
        self.assert_rejected(self.signup("abcdefghijkl"), self.classes_text())

    def classes_text(self):
        return by_level("uppercase and lowercase letters", "uppercase letter", "uppercase letter")

    def test_uat_1_3_common_password_rejected(self):
        """1.3 Password Password1234! (common): 201 at level 1, 400 (zxcvbn) from level 2."""
        response = self.signup("Password1234!")
        if LEVEL == 1:
            self.assertEqual(201, response.status_code, response.json)
        else:
            self.assert_rejected(response, "too easy to guess")

    def test_uat_1_4_password_with_username_rejected(self):
        """1.4 User juanperez with Juanperez-2024!: 201 at level 1, 400 from level 2."""
        response = self.signup("Juanperez-2024!", username="juanperez")
        if LEVEL == 1:
            self.assertEqual(201, response.status_code, response.json)
        else:
            self.assert_rejected(response, "must not contain your username")

    def test_uat_1_5_digit_sequence_rejected(self):
        """1.5 Password Abcd-19900101! (6+ digit sequence): 201 at level 1, 400 from level 2."""
        response = self.signup("Abcd-19900101!")
        if LEVEL == 1:
            self.assertEqual(201, response.status_code, response.json)
        else:
            self.assert_rejected(response, "sequences of 6 or more digits")

    def test_uat_1_6_long_passphrase_accepted(self):
        """1.6 Long passphrase caballo-verde-taza-lampara-7!: accepted."""
        # Without a capital letter it is rejected by the character classes
        self.assert_rejected(
            self.signup("caballo-verde-taza-lampara-7!", username="pass1"),
            self.classes_text(),
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
        """1.7 Change the own password without the current one: accepted at level 1, 400 from level 2."""
        user = self.make_user("regular", [VIEWER_ROLE], password="Kx9#tR2m!Qw7Zp")
        token = self.token_of("regular", "Kx9#tR2m!Qw7Zp")
        response = self.own_password_change(
            token, user.id, {"password": "Mv4#qL8n!Zr5Tw"}
        )
        if LEVEL == 1:
            self.assertEqual(200, response.status_code, response.json)
            # The change revokes the session: log in again with the new password
            token = self.token_of("regular", "Mv4#qL8n!Zr5Tw")
            response = self.own_password_change(
                token, user.id, {"password": "Hd6$vNc4&Ye2Bs", "current_password": "wrong"}
            )
            self.assertEqual(200, response.status_code, response.json)
            return
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn("current password is missing or incorrect", json.dumps(response.json))
        response = self.own_password_change(
            token, user.id, {"password": "Mv4#qL8n!Zr5Tw", "current_password": "wrong"}
        )
        self.assertEqual(400, response.status_code, response.json)

    def test_uat_1_8_trivial_variation_rejected(self):
        """1.8 Change Kx9#tR2m!Qw7Zp to Kx9#tR2m!Qw7Zq: accepted at level 1, too similar from level 2."""
        user = self.make_user("regular", [VIEWER_ROLE], password="Kx9#tR2m!Qw7Zp")
        token = self.token_of("regular", "Kx9#tR2m!Qw7Zp")
        response = self.own_password_change(
            token,
            user.id,
            {"password": "Kx9#tR2m!Qw7Zq", "current_password": "Kx9#tR2m!Qw7Zp"},
        )
        if LEVEL == 1:
            self.assertEqual(200, response.status_code, response.json)
            return
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn("too similar", json.dumps(response.json))

    def test_uat_1_9_password_reuse_rejected(self):
        """1.9 Change the password and set a previous one again: accepted at level 1, rejected from level 2."""
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
        if LEVEL == 1:
            self.assertEqual(200, response.status_code, response.json)
            # The history is kept at every level
            self.assertGreaterEqual(
                UserPasswordHistoryModel.query.filter_by(user_id=user.id).count(), 2
            )
            return
        self.assertEqual(400, response.status_code, response.json)
        self.assertIn("last 10 password", json.dumps(response.json))

    def test_uat_1_10_environment_cannot_weaken_the_minimum_length(self):
        """1.10 PWD_MIN_LENGTH=6: applied at level 1, raised to 12 with a warning at levels 2 and 3."""
        code = (
            "from cornflow.config import DefaultConfig; "
            "print(DefaultConfig.PWD_MIN_LENGTH); "
            "print([a.env_var for a in DefaultConfig.SECURITY_ADJUSTED_SETTINGS])"
        )
        env = {k: v for k, v in os.environ.items() if k not in SETTINGS_BY_ENV_VAR}
        env.update(
            {
                SECURITY_LEVEL_ENV_VAR: str(LEVEL),
                "PWD_MIN_LENGTH": "6",
                "FLASK_ENV": "testing",
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        effective = int(lines[-2])
        adjusted = lines[-1]
        if LEVEL == 1:
            self.assertEqual(6, effective)
            self.assertNotIn("PWD_MIN_LENGTH", adjusted)
            current_app.config["PWD_MIN_LENGTH"] = effective
            self.assert_rejected(self.signup("Ab3!x"), "at least 6 characters")
            response = self.signup("Ab3!xy")
            self.assertEqual(201, response.status_code, response.json)
        else:
            self.assertEqual(12, effective)
            self.assertIn("PWD_MIN_LENGTH", adjusted)
            current_app.config["PWD_MIN_LENGTH"] = effective
            self.assert_rejected(self.signup("Ab3!xyzQ"), "at least 12 characters")


class MfaLevelDefaultTests(UatTestCase):
    """Case 2.1: the MFA default of the level."""

    def test_uat_2_1_first_login_requires_mfa_setup(self):
        """2.1 First login of a new user: temporary token at level 3, direct token at levels 1 and 2."""
        self.make_user("newbie", [VIEWER_ROLE])
        response = self.login("newbie")
        self.assertEqual(200, response.status_code, response.json)
        if at_least(3):
            self.assertTrue(response.json["mfa_setup_required"])
            self.assertNotIn("token", response.json)
            temp_token = response.json["temp_token"]
            # The temporary token does not give access to other endpoints
            denied = self.client.get(INSTANCE_URL, headers=auth_header(temp_token))
            self.assertEqual(403, denied.status_code, denied.json)
            self.assertEqual("purpose_token", denied.json.get("error_code"))
        else:
            self.assertNotIn("mfa_setup_required", response.json)
            self.assertIn("token", response.json)
            # The voluntary enrollment is disabled by default at these levels
            setup = self.client.post(
                MFA_SETUP_URL, headers=auth_header(response.json["token"])
            )
            self.assertEqual(501, setup.status_code, setup.json)
            self.assertEqual({"error": MFA_ENROLLMENT_DISABLED_MESSAGE}, setup.json)


class MfaTests(UatTestCase):
    """Block 2: two-factor authentication (TOTP)."""

    config_overrides = MFA_ENROLLMENT_OVERRIDES

    def enrolled(self, username, role_ids=(VIEWER_ROLE,)):
        """Creates a user with MFA enabled and returns the enrollment response."""
        self.make_user(username, list(role_ids))
        response = self.login(username)
        self.assertEqual(200, response.status_code, response.json)
        if response.json.get("mfa_setup_required"):
            return self.enroll_mfa(response.json["temp_token"], username)
        # MFA is not mandatory at this level: enroll voluntarily
        return self.enroll_mfa(response.json["token"], username)

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
        """2.4 Log in with a valid TOTP code: 200 with the token (and the refresh token at level 3)."""
        self.enrolled("newbie")
        response = self.login("newbie", totp_code=self.totp_now("newbie"))
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        if at_least(3):
            self.assertIn("refresh_token", response.json)
        else:
            self.assertNotIn("refresh_token", response.json)

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

    def new_api_key(self, token, username):
        """Generates a personal API key; the TOTP code is only checked when API_KEY_STEPUP_TOTP=1."""
        response = self.client.post(
            API_KEY_URL,
            data=json.dumps({"totp_code": self.totp_now(username)}),
            headers=auth_header(token),
        )
        self.assertEqual(201, response.status_code, response.json)
        return response.json["api_key"]

    def test_uat_2_8_admin_resets_mfa_of_another_user(self):
        """2.8 An admin resets the MFA of another user: re-enroll, sessions and keys (also the one in its rotation grace) revoked."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        admin_token = self.token_of("cfadmin")
        verify = self.enrolled("victim")
        victim_id = UserModel.get_one_user_by_username("victim").id
        old_session = self.login("victim", totp_code=self.totp_now("victim")).json
        # The victim renews its API key: the superseded one stays valid during
        # the rotation grace window
        first_key = self.new_api_key(old_session["token"], "victim")
        second_key = self.new_api_key(old_session["token"], "victim")
        for key in (first_key, second_key):
            response = self.client.get(f"{USER_URL}{victim_id}/", headers=auth_header(key))
            self.assertEqual(200, response.status_code, response.json)
        key_version = UserModel.get_one_user_by_username("victim").api_key_version or 0

        response = self.client.delete(
            f"{USER_URL}{victim_id}/mfa/", headers=auth_header(admin_token)
        )
        self.assertEqual(200, response.status_code, response.json)

        db.session.expire_all()
        victim = UserModel.get_one_user_by_username("victim")
        self.assertFalse(victim.mfa_enabled)
        self.assertEqual(key_version + 1, victim.api_key_version)
        self.assertIsNone(victim.api_key_previous_version)
        self.assertIsNone(victim.api_key_grace_until)
        self.assertIsNone(victim.api_key_issued_at)
        # Both keys are revoked, also the one still in its grace window
        for key in (first_key, second_key):
            self.assert_invalid_token(
                self.client.get(f"{USER_URL}{victim_id}/", headers=auth_header(key)),
                API_KEY_REVOKED_MESSAGE,
            )
        # The sessions that existed are no longer valid
        stale = self.client.get(
            f"{USER_URL}{victim_id}/", headers=auth_header(old_session["token"])
        )
        self.assert_invalid_token(stale)
        if at_least(3):
            refreshed = self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": old_session["refresh_token"]}),
                headers={"Content-Type": "application/json"},
            )
            self.assert_invalid_token(refreshed)
            self.assertNotIn("token", refreshed.json)
        else:
            self.assertNotIn("refresh_token", old_session)
        # The next access requires a new enrollment when MFA is mandatory
        response = self.login("victim")
        self.assertEqual(200, response.status_code, response.json)
        if at_least(3):
            self.assertTrue(response.json["mfa_setup_required"])
            self.assertNotIn("token", response.json)
        else:
            self.assertIn("token", response.json)
            self.assertNotIn("mfa_required", response.json)
            self.assertNotIn("mfa_setup_required", response.json)
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
        """3.1 A user created by an admin logs in: change_password is false at level 1, true from level 2."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        self.make_user("cfplatform", [PLATFORM_ADMIN_ROLE])
        password = "Mv4#qL8n!Zr5Tw"
        payload = json.dumps(
            {"username": "provisioned", "email": "prov@example.com", "password": password}
        )
        if not at_least(2):
            self.assertEqual(1, LEVEL)
        else:
            denied = self.client.post(
                SIGNUP_URL, data=payload, headers=auth_header(self.token_of("cfadmin"))
            )
            self.assertEqual(403, denied.status_code, denied.json)
            self.assertIn(
                "Only a platform administrator can create users on this deployment",
                json.dumps(denied.json),
            )
        created = self.client.post(
            SIGNUP_URL,
            data=payload,
            headers=auth_header(self.token_of(SIGNUP_ADMIN)),
        )
        self.assertEqual(201, created.status_code, created.json)
        body = self.login("provisioned", password).json
        if body.get("mfa_setup_required"):
            self.enroll_mfa(body["temp_token"], "provisioned")
            body = self.login("provisioned", password, self.totp_now("provisioned")).json
        self.assertIn("token", body)
        self.assertIs(by_level(False, True, True), body["change_password"])

    def test_uat_3_2_flagged_password_blocks_other_endpoints(self):
        """3.2 Password flagged for change, GET /instance/: 200 at level 1, 403 password_rotation from level 2."""
        self.make_user("regular", [VIEWER_ROLE])
        token = self.token_of("regular")
        self.flag_for_change("regular")
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        if LEVEL == 1:
            # The flag is ignored at level 1
            self.assertEqual(200, response.status_code, response.json)
            return
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
        code = self.totp_now("regular") if "regular" in self.mfa_secrets else None
        login = self.login("regular", new_password, code).json
        self.assertIs(False, login["change_password"])
        response = self.client.get(INSTANCE_URL, headers=auth_header(body["token"]))
        self.assertEqual(200, response.status_code, response.json)

    @ui_only("redirect to settings with the mandatory change notice and navigation lock")
    def test_uat_3_5_ui_redirects_to_settings_on_forced_change(self):
        """3.5 In the interface, log in with a forced change: redirect to settings."""



class ServiceRotationExemptionTests(UatTestCase):
    """Case 3.6: the service user is exempt from the rotation."""

    config_overrides = ROTATION_OVERRIDES

    def test_uat_3_6_service_user_exempt_from_rotation(self):
        """3.6 Service user with an old password: rotation is not required."""
        age = timedelta(days=int(current_app.config["PWD_ROTATION_TIME"]) + 35)
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


class FailedLoginTests(UatTestCase):
    """Block 4: failed logins (cases 4.1 and 4.8), with the lockout of the level."""

    def test_uat_4_1_failed_attempts_return_the_same_generic_error(self):
        """4.1 Wrong password attempts: the same generic error; locked from level 2 only."""
        self.make_user("lockme", [VIEWER_ROLE])
        unknown = self.login("nobody", "Wrong-password-0!")
        self.assertEqual(400, unknown.status_code)
        attempts = int(current_app.config["LOGIN_MAX_ATTEMPTS"]) or 5
        for _ in range(attempts):
            response = self.login("lockme", "Wrong-password-0!")
            self.assertEqual(unknown.status_code, response.status_code)
            self.assertEqual(unknown.json, response.json)
        self.assertEqual("Invalid credentials", unknown.json["error"])
        db.session.expire_all()
        user = UserModel.get_one_user_by_username("lockme")
        if LEVEL == 1:
            # No lockout by default: the failures are not counted
            self.assertFalse(user.locked)
            self.assertEqual(0, user.failed_login_attempts)
        else:
            self.assertEqual(5, current_app.config["LOGIN_MAX_ATTEMPTS"])
            # The attempt that triggered the lock did not reveal it either
            self.assertTrue(user.locked)

    def test_uat_4_8_service_user_is_never_locked(self):
        """4.8 Failed attempts on the service user: not locked, warning logged."""
        self.make_user("service_user", [SERVICE_ROLE])
        attempts = max(int(current_app.config["LOGIN_MAX_ATTEMPTS"]), 5) + 1
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


class LockoutTests(UatTestCase):
    """Block 4: account lockout (cases 4.2 to 4.5), on at level 1 with LOGIN_MAX_ATTEMPTS=3."""

    config_overrides = LOCKOUT_OVERRIDES

    def test_uat_4_2_locked_account_with_correct_password(self):
        """4.2 After the lock, the correct password: 403 account_locked."""
        self.make_user("lockme", [VIEWER_ROLE])
        self.lock_account("lockme")
        response = self.login("lockme")
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("account_locked", response.json["error_code"])
        # With a wrong password the lock is not revealed
        wrong = self.login("lockme", "Wrong-password-0!")
        self.assertEqual(400, wrong.status_code)
        self.assertNotIn("error_code", wrong.json)

    def test_uat_4_3_client_admin_cannot_unlock(self):
        """4.3 Unlock with a client administrator: only platform admins at level 3; non-platform users at levels 1 and 2."""
        self.make_user("cfadmin", [ADMIN_ROLE])
        admin_token = self.token_of("cfadmin")
        target = self.make_user("lockme", [VIEWER_ROLE])
        self.lock_account("lockme")
        response = self.client.put(
            f"{USER_URL}{target.id}/unlock/", headers=auth_header(admin_token)
        )
        if at_least(3):
            self.assertEqual(403, response.status_code, response.json)
            db.session.expire_all()
            self.assertTrue(UserModel.get_one_user_by_username("lockme").locked)
            return
        self.assertEqual(200, response.status_code, response.json)
        db.session.expire_all()
        self.assertFalse(UserModel.get_one_user_by_username("lockme").locked)
        self.assertEqual(200, self.login("lockme").status_code)
        # A platform user can only be unlocked by a platform administrator
        platform_target = self.make_user("plock", [PLATFORM_VIEWER_ROLE])
        self.lock_account("plock")
        response = self.client.put(
            f"{USER_URL}{platform_target.id}/unlock/", headers=auth_header(admin_token)
        )
        self.assertEqual(403, response.status_code, response.json)
        self.assertIn(
            "Only a platform administrator can unlock the account of a platform user",
            json.dumps(response.json),
        )
        db.session.expire_all()
        self.assertTrue(UserModel.get_one_user_by_username("plock").locked)

    def test_uat_4_4_platform_admin_unlocks(self):
        """4.4 Unlock with a platform administrator: 200 and the user can log in."""
        self.make_user("cfplatform", [PLATFORM_ADMIN_ROLE])
        platform_token = self.token_of("cfplatform")
        target = self.make_user("lockme", [VIEWER_ROLE])
        self.lock_account("lockme")
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
        self.lock_account("lockme")
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
        self.assertEqual("10 per minute", current_app.config["RATELIMIT_LOGIN"])
        # Correct logins of the service user (exempt from MFA) are not limited
        # below the limit, and failed ones are the only ones that count
        self.make_user("service_user", [SERVICE_ROLE])
        for i in range(12):
            response = self.login("service_user")
            self.assertEqual(200, response.status_code, (i, response.json))
        for i in range(limit_count("10 per minute")):
            response = self.login("nobody", "Wrong-password-0!")
            self.assertNotEqual(429, response.status_code, f"request {i + 1}")
        response = self.login("nobody", "Wrong-password-0!")
        self.assertEqual(429, response.status_code, response.json)
        self.assertEqual(
            RATE_LIMIT_MESSAGE, response.json.get("message", response.json.get("error"))
        )
        # The IP has used up its quota: not even a correct login gets through
        self.assertEqual(429, self.login("service_user").status_code)

    def test_uat_4_7_recover_password_and_refresh_are_limited(self):
        """4.7 Repeat 4.6 on recover-password and token/refresh: also 429."""
        self.assertEqual("5 per hour", current_app.config["RATELIMIT_RECOVER"])
        # Refresh shares the login limit
        response = self.assert_limited_after(
            current_app.config["RATELIMIT_LOGIN"],
            lambda: self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": "not-a-token"}),
                headers={"Content-Type": "application/json"},
            ),
        )
        self.assertEqual(
            str(limit_count(current_app.config["RATELIMIT_LOGIN"])),
            response.headers.get("X-RateLimit-Limit"),
        )
        limiter.reset()
        with self.fake_smtp():
            # The first 5 requests are answered (200), also the successful ones
            for i in range(5):
                answer = self.client.put(
                    RECOVER_PASSWORD_URL,
                    data=json.dumps({"email": "nobody@example.com"}),
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(200, answer.status_code, (i, answer.json))
            response = self.client.put(
                RECOVER_PASSWORD_URL,
                data=json.dumps({"email": "nobody@example.com"}),
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(429, response.status_code, response.json)
        self.assertEqual(
            RATE_LIMIT_MESSAGE, response.json.get("message", response.json.get("error"))
        )
        self.assertEqual(
            str(limit_count(current_app.config["RATELIMIT_RECOVER"])),
            response.headers.get("X-RateLimit-Limit"),
        )


if __name__ == "__main__":
    unittest.main()
