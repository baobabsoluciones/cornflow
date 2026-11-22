"""
Unit tests for the behaviour of the BI token at each security level: issuing
(with or without an expiration date), rejection of the tokens without "exp"
at level 3, the CLI commands that issue them and their help texts.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
from click.testing import CliRunner
from flask import current_app, request

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.config import app_config
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.authentication.auth import BIAuth
from cornflow.shared.const import INTERNAL_TOKEN_ISSUER, SERVICE_ROLE
from cornflow.shared.exceptions import (
    ConfigurationError,
    InvalidCredentials,
    InvalidToken,
    bearer_challenge,
)
from cornflow.tests.security_levels_support import security_level_config
from cornflow.tests.unit.test_invalid_token_response import (
    BI_TEST_URL,
    CHALLENGE_HEADER,
    MSG_BI_EXPIRED,
    MSG_BI_INVALID,
    STRONG_PASSWORD,
    TokenSupport,
    auth_header,
)

MSG_BI_NO_EXPIRY = (
    "The BI token has no expiration date and is no longer accepted, "
    "please regenerate the BI token"
)
DAY = 86400
OTHER_KEY = "another-secret-key-of-at-least-32-bytes"


def last_line(text):
    return [line for line in text.strip().splitlines() if line.strip()][-1].strip()


class BITokenLevelCases:
    class Base(TokenSupport.Base):
        security_level = 1
        default_days = 0
        rejects_without_exp = False

        def create_app(self):
            app = super().create_app()

            def view():
                user = BIAuth().get_user_from_header(request.headers)
                return {"id": user.id}

            app.add_url_rule(BI_TEST_URL, "test_bi_auth", view)
            return app

        def setUp(self):
            super().setUp()
            # Read once: creating another app in a test detaches the instance
            self.user_id = self.user.id
            service = UserModel(
                data={
                    "username": "svc_bi",
                    "email": "svc_bi@test.com",
                    "password": STRONG_PASSWORD,
                }
            )
            service.save()
            UserRoleModel({"user_id": service.id, "role_id": SERVICE_ROLE}).save()

        # -- helpers -----------------------------------------------------

        def bi_token(self, key=None, **claims):
            payload = {
                "iat": datetime.now(timezone.utc),
                "sub": "ana",
                "iss": INTERNAL_TOKEN_ISSUER,
            }
            payload.update(claims)
            payload = {k: v for k, v in payload.items() if v is not None}
            return jwt.encode(
                payload, key or current_app.config["SECRET_BI_KEY"], algorithm="HS256"
            )

        def claims_of(self, token):
            return jwt.decode(token, options={"verify_signature": False})

        def assert_expiry(self, payload, days):
            if days > 0:
                self.assertIn("exp", payload)
                self.assertEqual(days * DAY, payload["exp"] - payload["iat"])
            else:
                self.assertNotIn("exp", payload)

        def run_cli(self, args, **overrides):
            name = security_level_config(self.security_level, **overrides)
            env = {
                "FLASK_ENV": name,
                "DATABASE_URL": app_config[name].SQLALCHEMY_DATABASE_URI,
                "EXTERNAL_APP": "0",
            }
            with mock.patch.dict(os.environ, env):
                return CliRunner().invoke(cli, args)

        def get(self, token):
            return self.client.get(BI_TEST_URL, headers=auth_header(token))

        def assert_rejected_or_valid(self, token, message=MSG_BI_NO_EXPIRY):
            """Level 3 rejects the token with the given message, others accept."""
            if self.rejects_without_exp:
                with self.assertRaises(InvalidToken) as ctx:
                    BIAuth.decode_token(token)
                self.assertEqual(401, ctx.exception.status_code)
                self.assertEqual(message, ctx.exception.error)
                self.assertEqual(
                    bearer_challenge(message), ctx.exception.headers[CHALLENGE_HEADER]
                )
            else:
                self.assertEqual("ana", BIAuth.decode_token(token)["sub"])

        # -- issuing -----------------------------------------------------

        def test_default_duration(self):
            token = BIAuth.generate_token(self.user.id)
            claims = self.claims_of(token)
            self.assert_expiry(claims, self.default_days)
            self.assertEqual("ana", claims["sub"])
            self.assertIn("iat", claims)
            self.assertEqual(INTERNAL_TOKEN_ISSUER, claims["iss"])

        def test_operator_duration(self):
            current_app.config["BI_TOKEN_DURATION_DAYS"] = 30
            claims = self.claims_of(BIAuth.generate_token(self.user.id))
            self.assert_expiry(claims, 30)

        def test_generated_token_is_accepted(self):
            token = BIAuth.generate_token(self.user.id)
            self.assertEqual("ana", BIAuth.decode_token(token)["sub"])
            response = self.get(token)
            self.assertEqual(200, response.status_code, response.json)
            self.assertEqual(self.user.id, response.json["id"])

        # -- decoding ----------------------------------------------------

        def test_token_without_exp(self):
            self.assert_rejected_or_valid(self.bi_token())

        def test_legacy_token_without_exp_and_iss(self):
            self.assert_rejected_or_valid(self.bi_token(iss=None))

        def test_http_token_without_exp(self):
            response = self.get(self.bi_token())
            if self.rejects_without_exp:
                self.assert_invalid_token(response, MSG_BI_NO_EXPIRY)
            else:
                self.assertEqual(200, response.status_code, response.json)
                self.assertEqual(self.user.id, response.json["id"])

        def test_token_with_exp_is_honoured(self):
            now = datetime.now(timezone.utc)
            token = self.bi_token(
                iat=now - timedelta(days=10), exp=now + timedelta(days=80)
            )
            self.assertEqual("ana", BIAuth.decode_token(token)["sub"])
            response = self.get(token)
            self.assertEqual(200, response.status_code, response.json)

        def test_expired_token_is_401(self):
            token = self.bi_token(exp=datetime.now(timezone.utc) - timedelta(hours=1))
            with self.assertRaises(InvalidToken) as ctx:
                BIAuth.decode_token(token)
            self.assertEqual(MSG_BI_EXPIRED, ctx.exception.error)
            self.assertEqual(
                bearer_challenge(MSG_BI_EXPIRED),
                ctx.exception.headers[CHALLENGE_HEADER],
            )
            self.assert_invalid_token(self.get(token), MSG_BI_EXPIRED)

        def test_bad_signature_is_401_generic(self):
            future = datetime.now(timezone.utc) + timedelta(days=30)
            tokens = {
                "without_exp": self.bi_token(key=OTHER_KEY),
                "with_exp": self.bi_token(key=OTHER_KEY, exp=future),
            }
            for name, token in tokens.items():
                with self.subTest(token=name):
                    with self.assertRaises(InvalidToken) as ctx:
                        BIAuth.decode_token(token)
                    self.assertEqual(MSG_BI_INVALID, ctx.exception.error)
                    self.assertEqual(
                        bearer_challenge(MSG_BI_INVALID),
                        ctx.exception.headers[CHALLENGE_HEADER],
                    )

        def test_empty_token_is_400_without_challenge(self):
            for token in ("", None):
                with self.subTest(token=token):
                    with self.assertRaises(InvalidCredentials) as ctx:
                        BIAuth.decode_token(token)
                    self.assertNotIsInstance(ctx.exception, InvalidToken)
                    self.assertEqual(400, ctx.exception.status_code)
                    self.assertNotIn(CHALLENGE_HEADER, ctx.exception.headers)

        def test_rule_depends_only_on_level(self):
            current_app.config["BI_TOKEN_DURATION_DAYS"] = 30
            self.assert_rejected_or_valid(self.bi_token())
            self.assertEqual(self.rejects_without_exp, BIAuth.expiry_required())

        # -- CLI ---------------------------------------------------------

        def test_cli_bi_token(self):
            result = self.run_cli(["users", "bi_token", "-u", "ana"])
            self.assertEqual(0, result.exit_code, result.output)
            token = last_line(result.output)
            self.assert_expiry(self.claims_of(token), self.default_days)
            self.assertEqual("ana", BIAuth.decode_token(token)["sub"])

        def test_cli_create_token(self):
            result = self.run_cli(
                [
                    "users",
                    "create",
                    "token",
                    "-i",
                    str(self.user.id),
                    "-u",
                    "svc_bi",
                    "-p",
                    STRONG_PASSWORD,
                ]
            )
            self.assertEqual(0, result.exit_code, result.output)
            token = last_line(result.output)
            self.assert_expiry(self.claims_of(token), self.default_days)
            self.assertEqual("ana", BIAuth.decode_token(token)["sub"])

        def test_cli_bi_token_with_operator_duration(self):
            result = self.run_cli(
                ["users", "bi_token", "-u", "ana"], BI_TOKEN_DURATION_DAYS=30
            )
            self.assertEqual(0, result.exit_code, result.output)
            self.assert_expiry(self.claims_of(last_line(result.output)), 30)

        def token_from_app(self, **overrides):
            app = create_app(security_level_config(self.security_level, **overrides))
            with app.app_context():
                return app, BIAuth.generate_token(self.user_id)


class LowLevelCases:
    class Base(BITokenLevelCases.Base):
        def test_zero_and_negative_mean_no_exp(self):
            for value in (0, -5):
                with self.subTest(value=value):
                    app, _ = self.token_from_app(BI_TOKEN_DURATION_DAYS=value)
                    self.assertEqual(value, app.config["BI_TOKEN_DURATION_DAYS"])
                    current_app.config["BI_TOKEN_DURATION_DAYS"] = value
                    token = BIAuth.generate_token(self.user_id)
                    self.assertNotIn("exp", self.claims_of(token))
                    self.assertEqual("ana", BIAuth.decode_token(token)["sub"])


class TestBITokenExpiryLevel1(LowLevelCases.Base):
    security_level = 1
    default_days = 0
    rejects_without_exp = False

    def test_no_upper_bound_at_level_1(self):
        app, token = self.token_from_app(BI_TOKEN_DURATION_DAYS=400)
        self.assertEqual(400, app.config["BI_TOKEN_DURATION_DAYS"])
        self.assert_expiry(self.claims_of(token), 400)


class TestBITokenExpiryLevel2(LowLevelCases.Base):
    security_level = 2
    default_days = 0
    rejects_without_exp = False


class TestBITokenExpiryLevel3(BITokenLevelCases.Base):
    security_level = 3
    default_days = 90
    rejects_without_exp = True

    def test_level_3_caps_at_365(self):
        app, token = self.token_from_app(BI_TOKEN_DURATION_DAYS=500)
        self.assertEqual(365, app.config["BI_TOKEN_DURATION_DAYS"])
        self.assert_expiry(self.claims_of(token), 365)

    def test_level_3_cli_does_not_start_with_zero(self):
        for value in (0, -5):
            with self.subTest(value=value):
                result = self.run_cli(
                    ["users", "bi_token", "-u", "ana"], BI_TOKEN_DURATION_DAYS=value
                )
                self.assertNotEqual(0, result.exit_code)
                self.assertIsInstance(result.exception, ConfigurationError)
                self.assertIn("BI_TOKEN_DURATION_DAYS", str(result.exception.error))
                for line in result.output.splitlines():
                    self.assertFalse(line.strip().startswith("ey"), line)


class TestBITokenCliHelp(unittest.TestCase):
    def help_text(self, *args):
        result = CliRunner().invoke(cli, [*args, "--help"])
        self.assertEqual(0, result.exit_code, result.output)
        return " ".join(result.output.split())

    def test_bi_token_help(self):
        text = self.help_text("users", "bi_token")
        for expected in (
            "expires after BI_TOKEN_DURATION_DAYS days",
            "does not expire when BI_TOKEN_DURATION_DAYS is 0",
            "[DEPRECATED]",
            "read-only personal API keys",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("never", text.lower())

    def test_create_token_help(self):
        text = self.help_text("users", "create", "token")
        for expected in (
            "expires after BI_TOKEN_DURATION_DAYS days",
            "does not expire when BI_TOKEN_DURATION_DAYS is 0",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("never", text.lower())


if __name__ == "__main__":
    unittest.main()
