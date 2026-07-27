"""
Unit tests for the CCN-STIC-807 security hardening features:

- Strengthened password policy (length, character variety, personal data,
  digit sequences, zxcvbn strength / common passwords, passphrases)
- Password history (no reuse of the last passwords) and similarity checks
- Hard enforcement of the password rotation
- Two-factor authentication (TOTP) enrollment, login and reset
"""

import json
import logging
import os
import re
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pyotp
from flask import Flask, current_app
from flask_testing import TestCase

from cornflow.app import MINIMUM_SECRET_KEY_LENGTH, _check_secret_keys, create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication.auth import BIAuth
from cornflow.shared.const import ADMIN_ROLE, PLATFORM_ADMIN_ROLE, SERVICE_ROLE
from cornflow.shared.exceptions import InvalidCredentials
from cornflow.shared.security import resolve_cors_origins
from cornflow.shared.validators import check_password_pattern, passwords_too_similar
from cornflow.tests.const import LOGIN_URL, SIGNUP_URL, USER_URL, INSTANCE_URL

ROLES_URL = "/roles/"
PERMISSION_URL = "/permission/"

MFA_SETUP_URL = "/mfa/setup/"
MFA_VERIFY_URL = "/mfa/verify/"

STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
OTHER_STRONG_PASSWORD = "Nw5@rT8y!Kd3Zx"

JSON_HEADER = {"Content-Type": "application/json"}


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


class TestPasswordPolicy(TestCase):
    """
    Tests for check_password_pattern and passwords_too_similar
    """

    def create_app(self):
        return create_app("testing")

    def test_none_password_is_allowed(self):
        # LDAP / OID users do not store a password
        check, _ = check_password_pattern(None)
        self.assertTrue(check)

    def test_minimum_length(self):
        check, msg = check_password_pattern("Sh0rt!aA")
        self.assertFalse(check)
        self.assertIn("12", msg)

    def test_character_variety(self):
        checks = {
            "missing upper": "kx9#tr2m!qw7zp",
            "missing lower": "KX9#TR2M!QW7ZP",
            "missing digit": "Kxw#tRsm!QwbZp",
            "missing special": "Kx9atR2mfQw7Zp",
        }
        for name, password in checks.items():
            check, _ = check_password_pattern(password)
            self.assertFalse(check, msg=f"{name} should be rejected")

    def test_no_whitespace(self):
        check, msg = check_password_pattern("Kx9#tR2m !Qw7Zp")
        self.assertFalse(check)
        self.assertIn("whitespace", msg)

    def test_no_six_digit_sequences(self):
        # Dates or other long digit runs are not allowed
        check, msg = check_password_pattern("Aa!x19911225Zt")
        self.assertFalse(check)
        self.assertIn("digits", msg)

    def test_no_personal_information(self):
        user_data = {
            "username": "gonzalo77",
            "first_name": "Gonzalo",
            "last_name": "Serrano",
            "email": "gonzalo.serrano@example.com",
        }
        for password in [
            "AGonzalo77#2x!Pw",
            "XxSerrano!9#Qwe",
            "A1!gonzalo.serrano#B",
        ]:
            check, msg = check_password_pattern(password, user_data=user_data)
            self.assertFalse(check, msg=f"{password} should be rejected")
            self.assertIn("username", msg)

    def test_common_passwords_rejected(self):
        # Classic patterns that fulfil the character rules but are guessable
        for password in ["Password2024!", "Qwerty123456!a", "Admin1234567!"]:
            check, _ = check_password_pattern(password)
            self.assertFalse(check, msg=f"{password} should be rejected")

    def test_strong_password_accepted(self):
        check, msg = check_password_pattern(STRONG_PASSWORD)
        self.assertTrue(check, msg=msg)

    def test_passphrase_accepted(self):
        # A long passphrase made of several words (joined without spaces)
        # is a valid password
        check, msg = check_password_pattern("Correcto.caballo-Grapa7.pila!")
        self.assertTrue(check, msg=msg)

    def test_passwords_too_similar(self):
        self.assertTrue(passwords_too_similar("Kx9#tR2m!Qw7Zp", "Kx9#tR2m!Qw7Z9"))
        self.assertTrue(passwords_too_similar("Kx9#tR2m!Qw7Zp", "kx9#tr2m!qw7zp"))
        self.assertFalse(
            passwords_too_similar("Kx9#tR2m!Qw7Zp", "Nw5@rT8y!Kd3Zx")
        )


class TestPasswordRotationEnforcement(TestCase):
    """
    Tests that users with an expired or flagged password can only reach the
    endpoints needed to change it.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "rotationuser",
            "email": "rotation@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": self.user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def expire_password(self):
        current_app.config["PWD_ROTATION_TIME"] = 1
        user = UserModel.get_one_user(self.user_id)
        user.pwd_last_change = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.add(user)
        db.session.commit()

    def test_expired_password_blocks_endpoints(self):
        response = self.client.get(
            INSTANCE_URL, headers=auth_header(self.token)
        )
        self.assertEqual(200, response.status_code)

        self.expire_password()

        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(403, response.status_code)
        self.assertEqual("password_rotation", response.json.get("error_code"))

    def test_expired_password_allows_own_user_and_change(self):
        self.expire_password()

        # Reading their own profile is still possible
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(self.token)
        )
        self.assertEqual(200, response.status_code)

        # Changing the password is still possible and unblocks the account
        response = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps(
                {
                    "password": OTHER_STRONG_PASSWORD,
                    "current_password": self.user_data["password"],
                }
            ),
            headers=auth_header(self.token),
        )
        self.assertEqual(200, response.status_code)

        # The password change revoked the session: a new login is needed
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(401, response.status_code)

        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": OTHER_STRONG_PASSWORD,
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        self.assertEqual(200, response.status_code)

    def test_forced_change_flag_blocks_endpoints(self):
        user = UserModel.get_one_user(self.user_id)
        user.pwd_change_required = True
        db.session.add(user)
        db.session.commit()

        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(403, response.status_code)
        self.assertEqual("password_rotation", response.json.get("error_code"))

        # The login response carries the change_password flag
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": self.user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json["change_password"])

    def test_admin_reset_forces_change(self):
        admin_data = {
            "username": "rotationadmin",
            "email": "rotationadmin@test.com",
            "password": OTHER_STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(admin_data), headers=JSON_HEADER
        )
        admin_id = response.json["id"]
        from cornflow.shared.const import ADMIN_ROLE

        UserRoleModel({"user_id": admin_id, "role_id": ADMIN_ROLE}).save()
        admin_token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": admin_data["username"],
                    "password": admin_data["password"],
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]

        response = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps({"password": "Jp7$nD3v!Bf8Tk"}),
            headers=auth_header(admin_token),
        )
        self.assertEqual(200, response.status_code)

        user = UserModel.get_one_user(self.user_id)
        self.assertTrue(user.pwd_change_required)


class TestRoleScoping(TestCase):
    """
    Tests that platform-only endpoints (roles, permissions) are reachable by
    platform administrators but not client administrators, that platform
    admin is a superset (still reaches the client-admin endpoints), and that
    only platform admins can revoke the admin role.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.admin_token = self.create_user_with_role(
            "clientadmin", "clientadmin@test.com", ADMIN_ROLE
        )
        self.platform_token = self.create_user_with_role(
            "platformadmin", "platformadmin@test.com", PLATFORM_ADMIN_ROLE
        )
        # A plain user, target for the revoke-admin tests
        self.target_id = self._signup(
            "targetadmin", "targetadmin@test.com"
        )
        UserRoleModel({"user_id": self.target_id, "role_id": ADMIN_ROLE}).save()
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _signup(self, username, email):
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": username,
                    "email": email,
                    "password": STRONG_PASSWORD,
                }
            ),
            headers=JSON_HEADER,
        )
        return response.json["id"]

    def create_user_with_role(self, username, email, role_id):
        user_id = self._signup(username, email)
        UserRoleModel({"user_id": user_id, "role_id": role_id}).save()
        return self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": STRONG_PASSWORD}),
            headers=JSON_HEADER,
        ).json["token"]

    def get(self, url, token):
        return self.client.get(url, headers=auth_header(token))

    def test_client_admin_denied_on_platform_endpoints(self):
        for url in (ROLES_URL, PERMISSION_URL, "/apiview/", "/action/"):
            response = self.get(url, self.admin_token)
            self.assertEqual(
                403, response.status_code, msg=f"admin should be denied {url}"
            )

    def test_platform_admin_allowed_on_platform_endpoints(self):
        for url in (ROLES_URL, PERMISSION_URL, "/apiview/", "/action/"):
            response = self.get(url, self.platform_token)
            self.assertEqual(
                200, response.status_code, msg=f"platform admin denied {url}"
            )

    def test_platform_admin_is_superset(self):
        # Platform admin also reaches the client-admin endpoints (user list)
        response = self.get(USER_URL, self.platform_token)
        self.assertEqual(200, response.status_code)

    def test_client_admin_keeps_user_management(self):
        response = self.get(USER_URL, self.admin_token)
        self.assertEqual(200, response.status_code)

    def test_client_admin_can_not_revoke_admin(self):
        response = self.client.put(
            f"{USER_URL}{self.target_id}/0/",
            headers=auth_header(self.admin_token),
        )
        self.assertEqual(403, response.status_code)
        # via the user/role delete path too
        response = self.client.delete(
            f"/user/role/{self.target_id}/{ADMIN_ROLE}/",
            headers=auth_header(self.admin_token),
        )
        self.assertEqual(403, response.status_code)

    def test_platform_admin_can_revoke_admin(self):
        response = self.client.put(
            f"{USER_URL}{self.target_id}/0/",
            headers=auth_header(self.platform_token),
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(
            UserRoleModel.is_admin(self.target_id),
        )

    def test_client_admin_can_assign_roles(self):
        # Assigning a (non-admin) role is still a client-admin power
        from cornflow.shared.const import VIEWER_ROLE

        response = self.client.post(
            "/user/role/",
            data=json.dumps({"user_id": self.target_id, "role_id": VIEWER_ROLE}),
            headers=auth_header(self.admin_token),
        )
        self.assertIn(response.status_code, (200, 201))


class TestBITokenExpiry(TestCase):
    """
    Tests that BI tokens now expire and that an expired one is rejected.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        self.user = UserModel(
            {
                "username": "bitoken",
                "email": "bitoken@test.com",
                "password": STRONG_PASSWORD,
            }
        )
        self.user.save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_valid_bi_token_decodes(self):
        token = BIAuth.generate_token(self.user.id)
        payload = BIAuth.decode_token(token)
        self.assertEqual("bitoken", payload["sub"])
        self.assertIn("exp", payload)

    def test_expired_bi_token_is_rejected(self):
        # Craft a token that expired an hour ago, signed with the BI key
        payload = {
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(days=100),
            "sub": self.user.username,
        }
        expired = jwt.encode(
            payload, current_app.config["SECRET_BI_KEY"], algorithm="HS256"
        )
        with self.assertRaises(InvalidCredentials):
            BIAuth.decode_token(expired)


class TestApiKey(TestCase):
    """
    Tests for the personal API key: generation behind a full session, use as
    a bearer credential, one-active-key semantics (regeneration revokes the
    previous), explicit revoke, the restriction away from security-sensitive
    endpoints, and the MFA step-up.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "apikeyuser",
            "email": "apikey@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.session_token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": self.user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def generate_key(self, token=None, totp_code=None):
        body = {}
        if totp_code is not None:
            body["totp_code"] = totp_code
        return self.client.post(
            "/user/api-key/",
            data=json.dumps(body),
            headers=auth_header(token or self.session_token),
        )

    def test_generate_and_use_api_key(self):
        response = self.generate_key()
        self.assertEqual(201, response.status_code)
        api_key = response.json["api_key"]
        self.assertIsNotNone(api_key)
        self.assertIn("expires_at", response.json)

        # The key authenticates a normal request (reading own profile)
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(api_key)
        )
        self.assertEqual(200, response.status_code)

    def test_api_key_forbidden_on_sensitive_endpoints(self):
        api_key = self.generate_key().json["api_key"]
        # Can not mint another API key with an API key
        response = self.generate_key(token=api_key)
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_forbidden", response.json.get("error_code"))
        # Can not change the password with an API key
        response = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps(
                {
                    "password": OTHER_STRONG_PASSWORD,
                    "current_password": self.user_data["password"],
                }
            ),
            headers=auth_header(api_key),
        )
        self.assertEqual(403, response.status_code)

    def test_regenerating_revokes_previous(self):
        first = self.generate_key().json["api_key"]
        # first works
        self.assertEqual(
            200,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(first)
            ).status_code,
        )
        second = self.generate_key().json["api_key"]
        # second works, first is now revoked
        self.assertEqual(
            200,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(second)
            ).status_code,
        )
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(first)
        )
        self.assertEqual(401, response.status_code)

    def test_revoke_api_key(self):
        api_key = self.generate_key().json["api_key"]
        response = self.client.delete(
            "/user/api-key/", headers=auth_header(self.session_token)
        )
        self.assertEqual(200, response.status_code)
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(api_key)
        )
        self.assertEqual(401, response.status_code)

    def test_lock_revokes_api_key(self):
        api_key = self.generate_key().json["api_key"]
        current_app.config["LOGIN_MAX_ATTEMPTS"] = 3
        for _ in range(3):
            self.client.post(
                LOGIN_URL,
                data=json.dumps(
                    {"username": self.user_data["username"], "password": "wrong"}
                ),
                headers=JSON_HEADER,
            )
        # The account is locked -> its API key is revoked too
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(api_key)
        )
        self.assertEqual(401, response.status_code)

    def test_step_up_totp_required_for_mfa_user(self):
        # Enable MFA on the user directly and reuse the still-valid session
        secret = pyotp.random_base32()
        user = UserModel.get_one_user(self.user_id)
        user.set_totp_secret(secret)
        user.mfa_enabled = True
        user.save()

        # Without a code -> rejected
        response = self.generate_key()
        self.assertEqual(400, response.status_code)
        # With a valid code -> issued
        response = self.generate_key(totp_code=pyotp.TOTP(secret).now())
        self.assertEqual(201, response.status_code)


class TestApiKeyDisabled(TestCase):
    """API key generation can be disabled per deployment."""

    def create_app(self):
        app = create_app("testing")
        app.config["PERSONAL_TOKEN_ENABLED"] = 0
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        data = {
            "username": "nokeyuser",
            "email": "nokey@test.com",
            "password": STRONG_PASSWORD,
        }
        self.client.post(SIGNUP_URL, data=json.dumps(data), headers=JSON_HEADER)
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": data["username"], "password": data["password"]}
            ),
            headers=JSON_HEADER,
        ).json["token"]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_generation_disabled(self):
        response = self.client.post(
            "/user/api-key/", data=json.dumps({}), headers=auth_header(self.token)
        )
        self.assertEqual(501, response.status_code)


class TestGetDbConn(unittest.TestCase):
    """
    Tests that the CLI database connection resolver honours DATABASE_URL so
    CLI commands run inside the container reach the same database as the
    server (the Docker image forces DEFAULT_POSTGRES=1).
    """

    def setUp(self):
        self._saved = {
            k: os.environ.get(k)
            for k in ("DATABASE_URL", "DEFAULT_POSTGRES", "CORNFLOW_DB_HOST")
        }

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_database_url_takes_precedence(self):
        from cornflow.cli.utils import get_db_conn

        os.environ["DEFAULT_POSTGRES"] = "1"
        os.environ["CORNFLOW_DB_HOST"] = "wrong_host"
        os.environ["DATABASE_URL"] = "postgresql://u:p@realhost:5432/realdb"
        self.assertEqual(
            "postgresql://u:p@realhost:5432/realdb", get_db_conn()
        )

    def test_falls_back_to_postgres_parts(self):
        from cornflow.cli.utils import get_db_conn

        os.environ.pop("DATABASE_URL", None)
        os.environ["DEFAULT_POSTGRES"] = "1"
        os.environ["CORNFLOW_DB_HOST"] = "somehost"
        self.assertIn("somehost", get_db_conn())


class TestConfigSecurityClamping(unittest.TestCase):
    """
    Tests that the helpers reading security configuration values from the
    environment clamp them to their floors/ceilings, so a tampered
    environment can not weaken the policy. The helpers are tested directly
    (with scratch variable names) to avoid reloading the config module,
    which would corrupt the app_config references used by other tests.
    """

    ENV_NAME = "CORNFLOW_TEST_CLAMP_VALUE"

    def tearDown(self):
        os.environ.pop(self.ENV_NAME, None)

    def _set(self, value):
        os.environ[self.ENV_NAME] = value

    def test_floor_blocks_weaker_values(self):
        from cornflow.config import _env_int_floor

        self._set("4")
        self.assertEqual(12, _env_int_floor(self.ENV_NAME, 12, 12))
        self._set("20")
        self.assertEqual(20, _env_int_floor(self.ENV_NAME, 12, 12))

    def test_ceiling_blocks_weaker_values(self):
        from cornflow.config import _env_float_ceiling, _env_int_ceiling

        self._set("9999")
        self.assertEqual(24, _env_int_ceiling(self.ENV_NAME, 8, 24))
        self.assertEqual(24.0, _env_float_ceiling(self.ENV_NAME, 8, 24))
        self._set("4")
        self.assertEqual(4, _env_int_ceiling(self.ENV_NAME, 8, 24))

    def test_invalid_values_fall_back_to_defaults(self):
        from cornflow.config import _env_int_ceiling, _env_int_floor

        self._set("not-a-number")
        self.assertEqual(12, _env_int_floor(self.ENV_NAME, 12, 12))
        self.assertEqual(8, _env_int_ceiling(self.ENV_NAME, 8, 24))

    def test_default_config_uses_hardened_values(self):
        from cornflow.config import DefaultConfig

        # The values loaded at import time must respect the thresholds
        # whatever the environment says
        self.assertLessEqual(DefaultConfig.TOKEN_DURATION, 24)
        self.assertLessEqual(DefaultConfig.PWD_ROTATION_TIME, 365)
        self.assertGreaterEqual(DefaultConfig.PWD_MIN_LENGTH, 12)
        self.assertGreaterEqual(DefaultConfig.PWD_MIN_ZXCVBN_SCORE, 3)
        self.assertGreaterEqual(DefaultConfig.PWD_HISTORY_SIZE, 10)
        self.assertLessEqual(DefaultConfig.PWD_MAX_SIMILARITY, 0.9)
        self.assertLessEqual(DefaultConfig.LOGIN_MAX_ATTEMPTS, 10)
        self.assertLessEqual(DefaultConfig.MFA_SETUP_TOKEN_DURATION_MINUTES, 30)


class TestSecretKeyLength(unittest.TestCase):
    """
    Tests that the application refuses to start with a JWT signing key
    shorter than 256 bits.
    """

    @staticmethod
    def build_app(token_key, bi_key):
        app = Flask(__name__)
        app.config["SECRET_TOKEN_KEY"] = token_key
        app.config["SECRET_BI_KEY"] = bi_key
        return app

    def test_short_secret_key_is_rejected(self):
        from cornflow.shared.exceptions import ConfigurationError

        long_key = "x" * MINIMUM_SECRET_KEY_LENGTH
        app = self.build_app("tooshort", long_key)
        with self.assertRaises(ConfigurationError):
            _check_secret_keys(app)

        app = self.build_app(long_key, "tooshort")
        with self.assertRaises(ConfigurationError):
            _check_secret_keys(app)

    def test_long_or_missing_keys_are_accepted(self):
        long_key = "x" * MINIMUM_SECRET_KEY_LENGTH
        _check_secret_keys(self.build_app(long_key, long_key))
        # Missing keys only log a warning: token generation fails at runtime
        _check_secret_keys(self.build_app(None, None))


class TestLoginLockout(TestCase):
    """
    Tests for the account lockout after too many failed login attempts.
    """

    def create_app(self):
        app = create_app("testing")
        app.config["LOGIN_MAX_ATTEMPTS"] = 3
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "lockoutuser",
            "email": "lockout@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self, password):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": password}
            ),
            headers=JSON_HEADER,
        )

    def test_lockout_after_max_attempts(self):
        # A wrong password always returns the same generic error (no
        # enumeration), even on the attempt that trips the lock
        for _ in range(3):
            response = self.log_in("Wrong#Password9!x")
            self.assertEqual(400, response.status_code)
            self.assertNotEqual("account_locked", response.json.get("error_code"))

        # The account is now locked: the lock is only revealed to a caller
        # that provides the correct password (the legitimate owner)
        self.assertTrue(UserModel.get_one_user(self.user_id).is_login_locked())
        response = self.log_in(self.user_data["password"])
        self.assertEqual(403, response.status_code)
        self.assertEqual("account_locked", response.json.get("error_code"))

    def create_user_with_role_and_token(self, username, email, role_id):
        """
        Creates a user through signup, assigns it a role and returns its
        session token.
        """
        data = {
            "username": username,
            "email": email,
            "password": OTHER_STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(data), headers=JSON_HEADER
        )
        UserRoleModel({"user_id": response.json["id"], "role_id": role_id}).save()
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": username, "password": data["password"]}
            ),
            headers=JSON_HEADER,
        ).json["token"]

    def test_lock_does_not_expire(self):
        for _ in range(3):
            self.log_in("Wrong#Password9!x")

        user = UserModel.get_one_user(self.user_id)
        self.assertTrue(user.is_login_locked())

        # The lock has no time window: the correct password keeps failing
        response = self.log_in(self.user_data["password"])
        self.assertEqual(403, response.status_code)
        self.assertEqual("account_locked", response.json.get("error_code"))

    def test_platform_admin_can_unlock(self):
        for _ in range(3):
            self.log_in("Wrong#Password9!x")
        self.assertTrue(UserModel.get_one_user(self.user_id).is_login_locked())

        token = self.create_user_with_role_and_token(
            "platformadmin", "platformadmin@test.com", PLATFORM_ADMIN_ROLE
        )
        response = self.client.put(
            f"{USER_URL}{self.user_id}/unlock/",
            headers=auth_header(token),
        )
        self.assertEqual(200, response.status_code)

        user = UserModel.get_one_user(self.user_id)
        self.assertFalse(user.is_login_locked())
        self.assertEqual(0, user.failed_login_attempts)

        response = self.log_in(self.user_data["password"])
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))

    def test_client_admin_cannot_unlock(self):
        for _ in range(3):
            self.log_in("Wrong#Password9!x")

        token = self.create_user_with_role_and_token(
            "clientadmin", "clientadmin@test.com", ADMIN_ROLE
        )
        response = self.client.put(
            f"{USER_URL}{self.user_id}/unlock/",
            headers=auth_header(token),
        )
        self.assertEqual(403, response.status_code)
        self.assertTrue(UserModel.get_one_user(self.user_id).is_login_locked())

    def test_successful_login_resets_counter(self):
        for _ in range(2):
            self.log_in("Wrong#Password9!x")

        response = self.log_in(self.user_data["password"])
        self.assertEqual(200, response.status_code)

        # After the reset, two more failures do not lock the account
        for _ in range(2):
            response = self.log_in("Wrong#Password9!x")
            self.assertEqual(400, response.status_code)
        self.assertNotEqual(
            "account_locked", response.json.get("error_code")
        )

    def test_service_user_exempt_from_lockout(self):
        service_data = {
            "username": "lockoutservice",
            "email": "lockoutservice@test.com",
            "password": "Sv7&kM2x!Bd5Ln",
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(service_data), headers=JSON_HEADER
        )
        UserRoleModel(
            {"user_id": response.json["id"], "role_id": SERVICE_ROLE}
        ).save()

        for _ in range(4):
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(
                    {
                        "username": service_data["username"],
                        "password": "Wrong#Password9!x",
                    }
                ),
                headers=JSON_HEADER,
            )
            self.assertEqual(400, response.status_code)

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": service_data["username"],
                    "password": service_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))


class TestRateLimiting(TestCase):
    """
    Tests the per-IP rate limiting of the sensitive unauthenticated
    endpoints (login and password recovery).
    """

    def create_app(self):
        # Dedicated config with rate limiting enabled from init_app time
        # (the base testing config keeps it off)
        return create_app("testing-ratelimit")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "ratelimit",
            "email": "ratelimit@test.com",
            "password": STRONG_PASSWORD,
        }
        self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        # Reset the shared limiter storage so counts do not leak between tests
        from cornflow.shared.rate_limit import limiter

        try:
            limiter.reset()
        except Exception:
            pass
        db.session.remove()
        db.drop_all()

    def try_login(self, password="wrong"):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": password}
            ),
            headers=JSON_HEADER,
        )

    def test_login_is_rate_limited_per_ip(self):
        # The limit is 3 per minute
        for _ in range(3):
            response = self.try_login()
            self.assertNotEqual(429, response.status_code)

        response = self.try_login()
        self.assertEqual(429, response.status_code)
        self.assertIn("Too many requests", response.json.get("message", ""))

    def test_rate_limit_counts_across_usernames(self):
        # Spraying different usernames from the same IP still hits the limit
        for i in range(3):
            self.client.post(
                LOGIN_URL,
                data=json.dumps(
                    {"username": f"sprayed{i}", "password": "whatever"}
                ),
                headers=JSON_HEADER,
            )
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": "sprayed99", "password": "whatever"}),
            headers=JSON_HEADER,
        )
        self.assertEqual(429, response.status_code)

    def test_recover_password_is_rate_limited(self):
        for _ in range(2):
            response = self.client.put(
                "/user/recover-password/",
                data=json.dumps({"email": "someone@test.com"}),
                headers=JSON_HEADER,
            )
            self.assertNotEqual(429, response.status_code)

        response = self.client.put(
            "/user/recover-password/",
            data=json.dumps({"email": "someone@test.com"}),
            headers=JSON_HEADER,
        )
        self.assertEqual(429, response.status_code)
        self.assertIn("Too many requests", response.json.get("message", ""))

    def test_token_refresh_is_rate_limited(self):
        # /token/refresh/ takes a credential in the body like login and
        # shares its per-IP limit (3 per minute in this config)
        for _ in range(3):
            response = self.client.post(
                "/token/refresh/",
                data=json.dumps({"refresh_token": "not-a-valid-token"}),
                headers=JSON_HEADER,
            )
            self.assertNotEqual(429, response.status_code)

        response = self.client.post(
            "/token/refresh/",
            data=json.dumps({"refresh_token": "not-a-valid-token"}),
            headers=JSON_HEADER,
        )
        self.assertEqual(429, response.status_code)

    def test_forwarded_for_used_when_trusted(self):
        current_app.config["RATELIMIT_TRUST_FORWARDED_FOR"] = 1
        # Different forwarded IPs are limited independently
        for _ in range(3):
            self.client.post(
                LOGIN_URL,
                data=json.dumps(
                    {"username": self.user_data["username"], "password": "x"}
                ),
                headers={**JSON_HEADER, "X-Forwarded-For": "10.0.0.1"},
            )
        # A different client IP still has budget
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": "x"}
            ),
            headers={**JSON_HEADER, "X-Forwarded-For": "10.0.0.2"},
        )
        self.assertNotEqual(429, response.status_code)
        # The first client IP is now blocked
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": "x"}
            ),
            headers={**JSON_HEADER, "X-Forwarded-For": "10.0.0.1"},
        )
        self.assertEqual(429, response.status_code)


class TestPasswordResetLink(TestCase):
    """
    Tests the password reset flow based on a time-limited, single-use link
    sent by email that points to the web client.
    """

    UI_URL = "https://cornflow-ui.test"

    def create_app(self):
        app = create_app("testing")
        app.config["CORNFLOW_UI_URL"] = self.UI_URL
        app.config["SERVICE_EMAIL_ADDRESS"] = "cornflow@test.com"
        app.config["SERVICE_EMAIL_PASSWORD"] = "not-used"
        app.config["SERVICE_EMAIL_SERVER"] = "smtp.test.com"
        app.config["SERVICE_EMAIL_PORT"] = 465
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "resetuser",
            "email": "reset@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def request_reset_link(self, email=None):
        """
        Requests a password recovery and returns the token extracted from
        the reset link in the (mocked) email.
        """
        with patch("cornflow.endpoints.user.send_email_to") as send_mock:
            response = self.client.put(
                "/user/recover-password/",
                data=json.dumps({"email": email or self.user_data["email"]}),
                headers=JSON_HEADER,
            )
            self.assertEqual(200, response.status_code)
            if not send_mock.called:
                return None
            email_body = send_mock.call_args.kwargs["email"]
        match = re.search(
            rf"{self.UI_URL}/reset-password\?token=([\w\.\-]+)", email_body
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def reset_password(self, token, new_password):
        return self.client.put(
            "/user/reset-password/",
            data=json.dumps({"password": new_password}),
            headers=auth_header(token),
        )

    def test_full_reset_flow(self):
        token = self.request_reset_link()
        self.assertIsNotNone(token)

        response = self.reset_password(token, OTHER_STRONG_PASSWORD)
        self.assertEqual(200, response.status_code)

        # The old password no longer works, the new one does
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": self.user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(400, response.status_code)
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": OTHER_STRONG_PASSWORD,
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))

    def test_reset_token_is_single_use(self):
        token = self.request_reset_link()
        response = self.reset_password(token, OTHER_STRONG_PASSWORD)
        self.assertEqual(200, response.status_code)

        # The same link can not be used again (the token was revoked)
        response = self.reset_password(token, "Jp7$nD3v!Bf8Tk")
        self.assertEqual(401, response.status_code)

    def test_reset_token_only_valid_on_reset_endpoint(self):
        token = self.request_reset_link()
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(token)
        )
        self.assertEqual(403, response.status_code)
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        self.assertEqual(403, response.status_code)

    def test_reset_rejects_weak_password(self):
        token = self.request_reset_link()
        response = self.reset_password(token, "weak")
        self.assertEqual(400, response.status_code)
        # The token is still valid after a rejected attempt
        response = self.reset_password(token, OTHER_STRONG_PASSWORD)
        self.assertEqual(200, response.status_code)

    def test_unknown_email_gets_same_response_and_no_email(self):
        token = self.request_reset_link(email="nobody@test.com")
        self.assertIsNone(token)

    def test_reset_clears_forced_change_flag(self):
        user = UserModel.get_one_user(self.user_id)
        user.pwd_change_required = True
        db.session.add(user)
        db.session.commit()

        token = self.request_reset_link()
        response = self.reset_password(token, OTHER_STRONG_PASSWORD)
        self.assertEqual(200, response.status_code)

        user = UserModel.get_one_user(self.user_id)
        self.assertFalse(user.pwd_change_required)


class TestLastLogin(TestCase):
    """
    Tests that the last-login timestamp is tracked and returned so the
    client can show the user their previous access.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "lastlogin",
            "email": "lastlogin@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.user_data["username"],
                    "password": self.user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )

    def test_last_login_is_tracked(self):
        # First login: there is no previous access
        response = self.log_in()
        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.json.get("last_login"))
        self.assertIsNotNone(
            UserModel.get_one_user(self.user_id).last_login_at
        )

        # Second login: the previous access is returned
        response = self.log_in()
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("last_login"))


class TestTokenRevocation(TestCase):
    """
    Tests that security events (password change, account lock) revoke every
    outstanding session token of the affected user.
    """

    def create_app(self):
        app = create_app("testing")
        app.config["LOGIN_MAX_ATTEMPTS"] = 3
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "revokeuser",
            "email": "revoke@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.token = self.log_in(self.user_data["password"]).json["token"]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self, password):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": password}
            ),
            headers=JSON_HEADER,
        )

    def test_password_change_revokes_sessions(self):
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(200, response.status_code)

        response = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps(
                {
                    "password": OTHER_STRONG_PASSWORD,
                    "current_password": self.user_data["password"],
                }
            ),
            headers=auth_header(self.token),
        )
        self.assertEqual(200, response.status_code)

        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(401, response.status_code)
        self.assertIn("revoked", response.json["error"].lower())

        # A fresh login with the new password issues a working token
        token = self.log_in(OTHER_STRONG_PASSWORD).json["token"]
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        self.assertEqual(200, response.status_code)

    def test_account_lock_revokes_sessions(self):
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(200, response.status_code)

        for _ in range(3):
            self.log_in("Wrong#Password9!x")

        # The lock revoked the existing session immediately
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(401, response.status_code)

    def test_admin_password_reset_revokes_sessions(self):
        admin_data = {
            "username": "revokeadmin",
            "email": "revokeadmin@test.com",
            "password": OTHER_STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(admin_data), headers=JSON_HEADER
        )
        UserRoleModel(
            {"user_id": response.json["id"], "role_id": ADMIN_ROLE}
        ).save()
        admin_token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": admin_data["username"],
                    "password": admin_data["password"],
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]

        response = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps({"password": "Jp7$nD3v!Bf8Tk"}),
            headers=auth_header(admin_token),
        )
        self.assertEqual(200, response.status_code)

        # The target user's session is gone; the admin's still works
        response = self.client.get(INSTANCE_URL, headers=auth_header(self.token))
        self.assertEqual(401, response.status_code)
        response = self.client.get(INSTANCE_URL, headers=auth_header(admin_token))
        self.assertEqual(200, response.status_code)


class TestMFAFlow(TestCase):
    """
    Tests for the two-factor authentication enrollment and login flow on a
    deployment where MFA is required.
    """

    def create_app(self):
        app = create_app("testing")
        app.config["MFA_REQUIRED"] = 1
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "mfauser",
            "email": "mfa@test.com",
            "password": STRONG_PASSWORD,
        }
        signup = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = signup.json["id"]
        self.signup_response = signup.json
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self, totp_code=None):
        payload = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        if totp_code is not None:
            payload["totp_code"] = totp_code
        return self.client.post(
            LOGIN_URL, data=json.dumps(payload), headers=JSON_HEADER
        )

    def enroll(self):
        """
        Completes the enrollment and returns (secret, backup_codes, token)
        """
        response = self.log_in()
        self.assertTrue(response.json.get("mfa_setup_required"))
        temp_token = response.json["temp_token"]

        setup = self.client.post(MFA_SETUP_URL, headers=auth_header(temp_token))
        self.assertEqual(200, setup.status_code)
        secret = setup.json["secret"]
        self.assertIn("provisioning_uri", setup.json)

        code = pyotp.TOTP(secret).now()
        verify = self.client.post(
            MFA_VERIFY_URL,
            data=json.dumps({"totp_code": code}),
            headers=auth_header(temp_token),
        )
        self.assertEqual(200, verify.status_code)
        return secret, verify.json["backup_codes"], verify.json["token"]

    def test_signup_returns_enrollment_token(self):
        self.assertTrue(self.signup_response.get("mfa_setup_required"))

    def test_login_requires_enrollment(self):
        response = self.log_in()
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json.get("mfa_setup_required"))
        self.assertNotIn("token", response.json)

    def test_temp_token_only_valid_for_mfa_endpoints(self):
        response = self.log_in()
        temp_token = response.json["temp_token"]
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(temp_token)
        )
        self.assertEqual(403, response.status_code)

    def test_full_enrollment_and_login(self):
        secret, backup_codes, token = self.enroll()
        self.assertEqual(
            int(current_app.config["MFA_BACKUP_CODES_NUMBER"]), len(backup_codes)
        )

        # The token issued after the verification is a full token
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(token)
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json["mfa_enabled"])

        # Login without code now asks for the code without failing
        response = self.log_in()
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json.get("mfa_required"))
        self.assertNotIn("token", response.json)

        # Login with a valid TOTP code returns a session token
        response = self.log_in(totp_code=pyotp.TOTP(secret).now())
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))

        # Login with an invalid code fails
        response = self.log_in(totp_code="000000")
        self.assertEqual(400, response.status_code)

    def test_totp_code_can_not_be_replayed(self):
        secret, _, _ = self.enroll()
        code = pyotp.TOTP(secret).now()

        response = self.log_in(totp_code=code)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))

        # The very same code can not be used again (replay within the window)
        response = self.log_in(totp_code=code)
        self.assertEqual(400, response.status_code)

    def test_backup_code_is_single_use(self):
        _, backup_codes, _ = self.enroll()
        code = backup_codes[0]

        response = self.log_in(totp_code=code)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))

        # The same backup code can not be used twice
        response = self.log_in(totp_code=code)
        self.assertEqual(400, response.status_code)

    def test_mfa_reset_forces_new_enrollment(self):
        secret, _, token = self.enroll()

        response = self.client.delete(
            f"{USER_URL}{self.user_id}/mfa/", headers=auth_header(token)
        )
        self.assertEqual(200, response.status_code)

        user = UserModel.get_one_user(self.user_id)
        self.assertFalse(user.mfa_enabled)
        self.assertIsNone(user.totp_secret)

        # Next login asks for enrollment again
        response = self.log_in()
        self.assertTrue(response.json.get("mfa_setup_required"))

    def test_wrong_totp_codes_lock_the_account(self):
        current_app.config["LOGIN_MAX_ATTEMPTS"] = 3
        secret, _, _ = self.enroll()

        for _ in range(2):
            response = self.log_in(totp_code="000000")
            self.assertEqual(400, response.status_code)

        # The attempt that reaches the limit locks the account
        response = self.log_in(totp_code="000000")
        self.assertEqual(403, response.status_code)
        self.assertEqual("account_locked", response.json.get("error_code"))

        # The account is now locked even with a valid code
        response = self.log_in(totp_code=pyotp.TOTP(secret).now())
        self.assertEqual(403, response.status_code)
        self.assertEqual("account_locked", response.json.get("error_code"))

    def test_service_user_is_exempt(self):
        service_data = {
            "username": "mfaservice",
            "email": "mfaservice@test.com",
            "password": "Sv7&kM2x!Bd5Ln",
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(service_data), headers=JSON_HEADER
        )
        service_id = response.json["id"]
        UserRoleModel({"user_id": service_id, "role_id": SERVICE_ROLE}).save()

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": service_data["username"],
                    "password": service_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json.get("token"))
        self.assertNotIn("mfa_setup_required", response.json)


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

    def events(self):
        return [r.get("event") for r in self.records]

    def by_event(self, event):
        return [r for r in self.records if r.get("event") == event]


class TestAuditLogging(TestCase):
    """
    Tests for the structured security audit log: each security-relevant
    event is emitted as a JSON record on the dedicated cornflow.audit logger.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "audituser",
            "email": "audit@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.audit_logger = logging.getLogger("cornflow.audit")
        self.capture = _AuditCapture()
        self.audit_logger.addHandler(self.capture)

    def tearDown(self):
        self.audit_logger.removeHandler(self.capture)
        db.session.remove()
        db.drop_all()

    def log_in(self, password):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.user_data["username"], "password": password}
            ),
            headers=JSON_HEADER,
        )

    def test_login_success_is_audited(self):
        self.log_in(self.user_data["password"])
        events = self.capture.by_event("login.success")
        self.assertEqual(1, len(events))
        record = events[0]
        # The record carries the mandatory schema fields
        self.assertTrue(record["audit"])
        self.assertEqual("success", record["outcome"])
        self.assertEqual(self.user_id, record["actor_id"])
        self.assertEqual(self.user_data["username"], record["actor"])
        self.assertIn("ts", record)

    def test_bad_password_is_audited_as_failure(self):
        self.log_in("Wrong#Password9!x")
        events = self.capture.by_event("login.failure")
        self.assertEqual(1, len(events))
        self.assertEqual("failure", events[0]["outcome"])
        self.assertEqual("bad_password", events[0]["reason"])

    def test_unknown_user_is_audited_as_failure(self):
        self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": "ghost", "password": STRONG_PASSWORD}),
            headers=JSON_HEADER,
        )
        events = self.capture.by_event("login.failure")
        self.assertEqual(1, len(events))
        self.assertEqual("unknown_user", events[0]["reason"])
        # The attempted username is recorded on the trusted audit channel
        self.assertEqual("ghost", events[0]["actor"])

    def test_password_change_is_audited(self):
        token = self.log_in(self.user_data["password"]).json["token"]
        self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps(
                {
                    "password": OTHER_STRONG_PASSWORD,
                    "current_password": self.user_data["password"],
                }
            ),
            headers=auth_header(token),
        )
        events = self.capture.by_event("password.changed")
        self.assertEqual(1, len(events))
        self.assertEqual(self.user_id, events[0]["target_id"])

    def test_audit_can_be_disabled(self):
        current_app.config["AUDIT_LOG_ENABLED"] = 0
        try:
            self.log_in(self.user_data["password"])
            self.assertEqual([], self.capture.records)
        finally:
            current_app.config["AUDIT_LOG_ENABLED"] = 1


class TestSecurityHeaders(TestCase):
    """
    Tests for the HTTP security response headers added on every response.
    """

    def create_app(self):
        return create_app("testing")

    def _get(self):
        # A 404 is enough: the after_request hook runs on every response and
        # this avoids needing the database or an Airflow connection.
        return self.client.get("/this-path-does-not-exist/")

    def test_headers_present(self):
        headers = self._get().headers
        self.assertEqual("nosniff", headers.get("X-Content-Type-Options"))
        self.assertEqual("DENY", headers.get("X-Frame-Options"))
        self.assertIn(
            "default-src 'none'", headers.get("Content-Security-Policy", "")
        )
        self.assertIn(
            "frame-ancestors 'none'", headers.get("Content-Security-Policy", "")
        )
        self.assertEqual("no-referrer", headers.get("Referrer-Policy"))
        self.assertIn("geolocation=()", headers.get("Permissions-Policy", ""))
        self.assertEqual("no-store", headers.get("Cache-Control"))
        # HSTS is off in the testing config (no TLS in front)
        self.assertNotIn("Strict-Transport-Security", headers)

    def test_hsts_present_when_enabled(self):
        current_app.config["HSTS_ENABLED"] = 1
        try:
            headers = self._get().headers
            self.assertIn(
                "max-age=", headers.get("Strict-Transport-Security", "")
            )
            self.assertIn(
                "includeSubDomains",
                headers.get("Strict-Transport-Security", ""),
            )
        finally:
            current_app.config["HSTS_ENABLED"] = 0

    def test_headers_can_be_disabled(self):
        current_app.config["SECURITY_HEADERS_ENABLED"] = 0
        try:
            self.assertNotIn("X-Content-Type-Options", self._get().headers)
        finally:
            current_app.config["SECURITY_HEADERS_ENABLED"] = 1


class TestCorsOrigins(unittest.TestCase):
    """
    Tests for the CORS_ORIGINS normalisation (default-closed in production).
    """

    def test_wildcard_allows_any(self):
        self.assertEqual("*", resolve_cors_origins("*"))
        self.assertEqual("*", resolve_cors_origins(["*"]))

    def test_empty_is_default_closed(self):
        self.assertEqual([], resolve_cors_origins(""))
        self.assertEqual([], resolve_cors_origins("   "))
        self.assertEqual([], resolve_cors_origins(None))

    def test_explicit_allow_list(self):
        self.assertEqual(
            ["https://a.example.com", "https://b.example.com"],
            resolve_cors_origins("https://a.example.com, https://b.example.com"),
        )


class TestDocsGating(unittest.TestCase):
    """
    Tests that the Swagger docs UI is registered only when DOCS_ENABLED is on.
    """

    def test_docs_enabled_serves_swagger(self):
        app = create_app("testing")
        response = app.test_client().get("/swagger-ui/")
        self.assertNotEqual(404, response.status_code)

    def test_docs_disabled_hides_swagger(self):
        from cornflow.config import Testing

        with patch.object(Testing, "DOCS_ENABLED", 0):
            app = create_app("testing")
        response = app.test_client().get("/swagger-ui/")
        self.assertEqual(404, response.status_code)
