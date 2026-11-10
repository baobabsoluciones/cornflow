"""
Everything in this module exists because of the unprefixed route aliases:
once they are dropped the module can be deleted (the security checks are
covered on the canonical routes by the rest of the suite).

Tests that the security checks (API key restrictions, purpose tokens,
password rotation and per-IP rate limiting) behave the same on the two routes
every core endpoint answers on: the canonical one under ``/cornflow`` and the
legacy one without prefix.
"""

import json
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    SIGNUP_WITH_AUTH,
    TOKEN_PURPOSE_MFA_SETUP,
    TOKEN_PURPOSE_PWD_RESET,
)

STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
NEW_PASSWORDS = ["Nw5@rT8y!Kd3Zx", "Jp7$nD3v!Bf8Tk"]

JSON_HEADER = {"Content-Type": "application/json"}

CANONICAL_PREFIX = "/cornflow"
LEGACY_PREFIX = ""
PREFIXES = [CANONICAL_PREFIX, LEGACY_PREFIX]


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


class SecurityRoutesBase(TestCase):
    """
    Creates a regular user and logs it in. Helpers send a request to a path
    on a given route prefix.
    """

    USERNAME = "routesuser"

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": self.USERNAME,
            "email": "routes@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            f"{CANONICAL_PREFIX}/signup/", data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        self.assertEqual(201, response.status_code)
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )
        self.token = self.log_in(self.user_data)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self, user_data, prefix=CANONICAL_PREFIX):
        response = self.client.post(
            f"{prefix}/login/",
            data=json.dumps(
                {
                    "username": user_data["username"],
                    "password": user_data["password"],
                }
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code)
        return response.json["token"]

    def request(self, method, prefix, path, token, body=None):
        return self.client.open(
            f"{prefix}{path}",
            method=method,
            data=json.dumps(body if body is not None else {}),
            headers=auth_header(token),
        )

    def create_other_user(self, name="otheruser"):
        data = {
            "username": name,
            "email": f"{name}@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            f"{CANONICAL_PREFIX}/signup/", data=json.dumps(data), headers=JSON_HEADER
        )
        self.assertEqual(201, response.status_code)
        return response.json["id"]


class TestApiKeyOnBothRoutes(SecurityRoutesBase):
    """
    A personal API key is refused on the security-sensitive endpoints
    whichever route is used, and keeps working on the rest.
    """

    def setUp(self):
        super().setUp()
        response = self.client.post(
            f"{CANONICAL_PREFIX}/user/api-key/",
            data=json.dumps({}),
            headers=auth_header(self.token),
        )
        self.assertEqual(201, response.status_code)
        self.api_key = response.json["api_key"]

    def forbidden_cases(self):
        uid = self.user_id
        return [
            ("POST", "/user/api-key/"),
            ("DELETE", "/user/api-key/"),
            ("POST", "/mfa/setup/"),
            ("POST", "/mfa/verify/"),
            ("DELETE", f"/user/{uid}/mfa/"),
            ("PUT", "/user/reset-password/"),
            ("PUT", f"/user/{uid}/"),
            ("DELETE", f"/user/{uid}/"),
            ("PUT", f"/user/{uid}/1/"),
            ("PUT", f"/user/{uid}/unlock/"),
            ("POST", "/roles/"),
            ("PUT", "/roles/1/"),
            ("DELETE", "/roles/1/"),
            ("POST", "/permission/"),
            ("PUT", "/permission/1/"),
            ("DELETE", "/permission/1/"),
            ("POST", "/user/role/"),
            ("DELETE", f"/user/role/{uid}/1/"),
        ]

    def assert_api_key_forbidden(self, response, label):
        self.assertEqual(403, response.status_code, msg=label)
        self.assertEqual(
            "api_key_forbidden", response.json.get("error_code"), msg=label
        )

    def test_forbidden_endpoints_on_both_routes(self):
        for prefix in PREFIXES:
            for method, path in self.forbidden_cases():
                label = f"{method} {prefix}{path}"
                with self.subTest(label):
                    response = self.request(method, prefix, path, self.api_key)
                    self.assert_api_key_forbidden(response, label)

    def test_signup_forbidden_on_both_routes(self):
        # Sign up only authenticates when it is configured to require auth
        current_app.config["SIGNUP_ACTIVATED"] = SIGNUP_WITH_AUTH
        body = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": STRONG_PASSWORD,
        }
        for prefix in PREFIXES:
            label = f"POST {prefix}/signup/"
            with self.subTest(label):
                response = self.request("POST", prefix, "/signup/", self.api_key, body)
                self.assert_api_key_forbidden(response, label)

    def test_allowed_methods_work_with_api_key_on_both_routes(self):
        for prefix in PREFIXES:
            with self.subTest(f"GET {prefix}/instance/"):
                response = self.request("GET", prefix, "/instance/", self.api_key)
                self.assertEqual(200, response.status_code)
            # user-detail is only forbidden for PUT and DELETE
            with self.subTest(f"GET {prefix}/user/<id>/"):
                response = self.request(
                    "GET", prefix, f"/user/{self.user_id}/", self.api_key
                )
                self.assertEqual(200, response.status_code)


class TestPurposeTokensOnBothRoutes(SecurityRoutesBase):
    """
    Temporary purpose tokens only reach their own endpoints, on both routes.
    """

    def purpose_token(self, purpose):
        return Auth.generate_token(self.user_id, purpose=purpose)

    def assert_purpose_rejected(self, response, label):
        self.assertEqual(403, response.status_code, msg=label)
        self.assertEqual("purpose_token", response.json.get("error_code"), msg=label)

    def assert_purpose_accepted(self, response, label):
        error_code = (response.json or {}).get("error_code")
        self.assertNotEqual("purpose_token", error_code, msg=label)

    def test_mfa_setup_token_reaches_mfa_setup_on_both_routes(self):
        for prefix in PREFIXES:
            label = f"POST {prefix}/mfa/setup/"
            with self.subTest(label):
                token = self.purpose_token(TOKEN_PURPOSE_MFA_SETUP)
                response = self.request("POST", prefix, "/mfa/setup/", token)
                self.assertEqual(200, response.status_code, msg=label)
                self.assertIn("secret", response.json)

    def test_mfa_setup_token_reaches_mfa_verify_on_both_routes(self):
        for prefix in PREFIXES:
            label = f"POST {prefix}/mfa/verify/"
            with self.subTest(label):
                token = self.purpose_token(TOKEN_PURPOSE_MFA_SETUP)
                # Without a started enrollment the code is refused, but not
                # because of the purpose of the token
                response = self.request(
                    "POST", prefix, "/mfa/verify/", token, {"totp_code": "000000"}
                )
                self.assert_purpose_accepted(response, label)
                self.assertNotEqual(403, response.status_code, msg=label)

    def test_mfa_setup_token_rejected_elsewhere_on_both_routes(self):
        cases = [
            ("GET", "/instance/"),
            ("GET", f"/user/{self.user_id}/"),
            ("PUT", "/user/reset-password/"),
        ]
        for prefix in PREFIXES:
            for method, path in cases:
                label = f"{method} {prefix}{path}"
                with self.subTest(label):
                    token = self.purpose_token(TOKEN_PURPOSE_MFA_SETUP)
                    response = self.request(
                        method, prefix, path, token, {"password": STRONG_PASSWORD}
                    )
                    self.assert_purpose_rejected(response, label)

    def test_pwd_reset_token_reaches_reset_password_on_both_routes(self):
        for prefix, new_password in zip(PREFIXES, NEW_PASSWORDS):
            label = f"PUT {prefix}/user/reset-password/"
            with self.subTest(label):
                # The password change revokes the token, so each route
                # needs a fresh one
                token = self.purpose_token(TOKEN_PURPOSE_PWD_RESET)
                response = self.request(
                    "PUT",
                    prefix,
                    "/user/reset-password/",
                    token,
                    {"password": new_password},
                )
                self.assertEqual(200, response.status_code, msg=label)

    def test_pwd_reset_token_rejected_elsewhere_on_both_routes(self):
        cases = [
            ("GET", "/instance/"),
            ("GET", f"/user/{self.user_id}/"),
            ("POST", "/mfa/setup/"),
            ("POST", "/mfa/verify/"),
        ]
        for prefix in PREFIXES:
            for method, path in cases:
                label = f"{method} {prefix}{path}"
                with self.subTest(label):
                    token = self.purpose_token(TOKEN_PURPOSE_PWD_RESET)
                    response = self.request(method, prefix, path, token)
                    self.assert_purpose_rejected(response, label)


class TestPasswordRotationOnBothRoutes(SecurityRoutesBase):
    """
    A user with an expired password only reaches the endpoints needed to
    change it, on both routes.
    """

    def setUp(self):
        super().setUp()
        self.other_id = self.create_other_user()
        self.expire_password()

    def expire_password(self):
        current_app.config["PWD_ROTATION_TIME"] = 1
        user = UserModel.get_one_user(self.user_id)
        user.pwd_last_change = datetime.now(timezone.utc) - timedelta(days=2)
        db.session.add(user)
        db.session.commit()

    def assert_rotation_rejected(self, response, label):
        self.assertEqual(403, response.status_code, msg=label)
        self.assertEqual(
            "password_rotation", response.json.get("error_code"), msg=label
        )

    def test_allowed_endpoints_on_both_routes(self):
        cases = [
            f"/user/{self.user_id}/",
            "/token/",
            "/user/role/",
        ]
        for prefix in PREFIXES:
            for path in cases:
                label = f"GET {prefix}{path}"
                with self.subTest(label):
                    response = self.request("GET", prefix, path, self.token)
                    self.assertEqual(200, response.status_code, msg=label)

    def test_own_password_change_on_both_routes(self):
        current = STRONG_PASSWORD
        for prefix, new_password in zip(PREFIXES, NEW_PASSWORDS):
            label = f"PUT {prefix}/user/<id>/"
            with self.subTest(label):
                # A password change unblocks the account and revokes the
                # session: expire it again and log in before each route
                self.expire_password()
                token = self.log_in(
                    {"username": self.USERNAME, "password": current}
                )
                response = self.request(
                    "PUT",
                    prefix,
                    f"/user/{self.user_id}/",
                    token,
                    {"password": new_password, "current_password": current},
                )
                self.assertEqual(200, response.status_code, msg=label)
                current = new_password

    def test_other_user_detail_rejected_on_both_routes(self):
        for prefix in PREFIXES:
            label = f"GET {prefix}/user/<other>/"
            with self.subTest(label):
                response = self.request(
                    "GET", prefix, f"/user/{self.other_id}/", self.token
                )
                self.assert_rotation_rejected(response, label)

    def test_other_endpoints_rejected_on_both_routes(self):
        cases = [
            ("GET", "/instance/"),
            ("GET", "/execution/"),
            ("GET", "/case/"),
            ("GET", "/user/"),
            ("DELETE", f"/user/{self.user_id}/"),
        ]
        for prefix in PREFIXES:
            for method, path in cases:
                label = f"{method} {prefix}{path}"
                with self.subTest(label):
                    response = self.request(method, prefix, path, self.token)
                    self.assert_rotation_rejected(response, label)


class TestRateLimitAcrossRoutes(TestCase):
    """
    The per-IP counters are shared by the canonical and the legacy route of
    the same endpoint. The rate limit config allows 3 logins per minute and
    2 password recoveries per hour.
    """

    LOGIN_LIMIT = 3
    RECOVER_LIMIT = 2

    def create_app(self):
        return create_app("testing-ratelimit")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "routeslimit",
            "email": "routeslimit@test.com",
            "password": STRONG_PASSWORD,
        }
        self.client.post(
            f"{CANONICAL_PREFIX}/signup/", data=json.dumps(self.user_data), headers=JSON_HEADER
        )
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        from cornflow.shared.rate_limit import limiter

        try:
            limiter.reset()
        except Exception:
            pass
        db.session.remove()
        db.drop_all()

    def try_login(self, prefix):
        return self.client.post(
            f"{prefix}/login/",
            data=json.dumps(
                {"username": self.user_data["username"], "password": "wrong"}
            ),
            headers=JSON_HEADER,
        )

    def try_recover(self, prefix):
        return self.client.put(
            f"{prefix}/user/recover-password/",
            data=json.dumps({"email": "someone@test.com"}),
            headers=JSON_HEADER,
        )

    def try_refresh(self, prefix):
        return self.client.post(
            f"{prefix}/token/refresh/",
            data=json.dumps({"refresh_token": "not-a-valid-token"}),
            headers=JSON_HEADER,
        )

    def try_reset(self, prefix):
        return self.client.put(
            f"{prefix}/user/reset-password/",
            data=json.dumps({"password": STRONG_PASSWORD}),
            headers=auth_header("not-a-valid-token"),
        )

    def alternate_until_limit(self, attempt, limit, first_prefix, last_prefix):
        """
        Spends the whole budget alternating routes (starting on first_prefix)
        and then tries once more on last_prefix.
        """
        order = [first_prefix, last_prefix]
        for i in range(limit):
            response = attempt(order[i % 2])
            self.assertNotEqual(429, response.status_code, msg=f"attempt {i + 1}")
        return attempt(last_prefix)

    def test_login_limit_shared_last_attempt_on_legacy_route(self):
        response = self.alternate_until_limit(
            self.try_login, self.LOGIN_LIMIT, CANONICAL_PREFIX, LEGACY_PREFIX
        )
        self.assertEqual(429, response.status_code)
        self.assertIn("Too many requests", response.json.get("message", ""))

    def test_login_limit_shared_last_attempt_on_canonical_route(self):
        response = self.alternate_until_limit(
            self.try_login, self.LOGIN_LIMIT, LEGACY_PREFIX, CANONICAL_PREFIX
        )
        self.assertEqual(429, response.status_code)
        self.assertIn("Too many requests", response.json.get("message", ""))

    def test_login_limit_exhausted_on_one_route_blocks_the_other(self):
        for _ in range(self.LOGIN_LIMIT):
            self.assertNotEqual(429, self.try_login(CANONICAL_PREFIX).status_code)
        self.assertEqual(429, self.try_login(CANONICAL_PREFIX).status_code)
        self.assertEqual(429, self.try_login(LEGACY_PREFIX).status_code)

    def test_recover_password_limit_shared_across_routes(self):
        response = self.alternate_until_limit(
            self.try_recover, self.RECOVER_LIMIT, CANONICAL_PREFIX, LEGACY_PREFIX
        )
        self.assertEqual(429, response.status_code)
        self.assertEqual(429, self.try_recover(CANONICAL_PREFIX).status_code)

    def test_token_refresh_limit_shared_across_routes(self):
        response = self.alternate_until_limit(
            self.try_refresh, self.LOGIN_LIMIT, CANONICAL_PREFIX, LEGACY_PREFIX
        )
        self.assertEqual(429, response.status_code)
        self.assertEqual(429, self.try_refresh(CANONICAL_PREFIX).status_code)

    def test_reset_password_limit_shared_across_routes(self):
        response = self.alternate_until_limit(
            self.try_reset, self.RECOVER_LIMIT, CANONICAL_PREFIX, LEGACY_PREFIX
        )
        self.assertEqual(429, response.status_code)
        self.assertEqual(429, self.try_reset(CANONICAL_PREFIX).status_code)
