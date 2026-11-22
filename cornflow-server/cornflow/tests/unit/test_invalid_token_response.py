"""
Unit tests for the 401 + WWW-Authenticate response given to the tokens that
are not valid (expired, bad signature or format, revoked, unknown user, refresh
token misused, BI token), the same at every security level.

The requests with no token to assess (400), the forbidden ones (403) and the
unexpected errors (500) must not carry the challenge.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import current_app, request
from flask_testing import TestCase

from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.models import SessionModel, UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication.auth import Auth, BIAuth, public_keys_cache
from cornflow.shared.const import (
    AUTH_OID,
    INTERNAL_TOKEN_ISSUER,
    PLANNER_ROLE,
    TOKEN_PURPOSE_PWD_RESET,
)
from cornflow.shared.exceptions import (
    CommunicationError,
    InvalidCredentials,
    InvalidToken,
    InvalidUsage,
    bearer_challenge,
)
from cornflow.tests.const import (
    INSTANCE_URL,
    LOGIN_URL,
    PREFIX,
    SCHEMA_URL,
    TOKEN_URL,
    USER_URL,
)
from cornflow.tests.security_levels_support import SecurityLevelTestMixin

REFRESH_URL = PREFIX + "/token/refresh/"
LOGOUT_URL = PREFIX + "/logout/"
BI_TEST_URL = "/test-bi-auth/"

CHALLENGE_HEADER = "WWW-Authenticate"
CHALLENGE_PREFIX = 'Bearer error="invalid_token", error_description="'
STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
JSON_HEADER = {"Content-Type": "application/json"}

MSG_EXPIRED = "The token has expired, please login again"
MSG_FORMAT = "Invalid token format or signature"
MSG_FORMAT_OIDC = "Invalid token format, signature, or configuration"
MSG_REVOKED = "The session has been revoked, please log in again"
MSG_CLOSED = "The session has been closed, please log in again"
MSG_SESSION_EXPIRED = "The session has expired, please log in again"
MSG_API_KEY = "The API key has been revoked, please generate a new one"
MSG_NO_USER = "User not found. Please ensure you are using valid credentials"
MSG_REFRESH_ON_ENDPOINT = "A refresh token can not be used to access this endpoint"
MSG_BI_EXPIRED = "The BI token has expired, please generate a new one"
MSG_BI_INVALID = "Invalid token, please try again with a new token"


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


def unquote_description(header_value):
    """Undoes the quoted-string escape of the error_description."""
    assert header_value.startswith(CHALLENGE_PREFIX), header_value
    assert header_value.endswith('"'), header_value
    inner = header_value[len(CHALLENGE_PREFIX) : -1]
    result, escaped = [], False
    for ch in inner:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        else:
            assert ch != '"', f"unescaped quote in {header_value}"
            result.append(ch)
    assert not escaped, header_value
    return "".join(result)


class TestBearerChallenge(unittest.TestCase):
    """Pure tests of the header value and of the exception (no app)."""

    def test_exact_value(self):
        self.assertEqual(
            'Bearer error="invalid_token", error_description='
            '"The token has expired, please login again"',
            bearer_challenge(MSG_EXPIRED),
        )

    def test_quotes_and_backslashes_are_escaped(self):
        self.assertEqual(
            'Bearer error="invalid_token", error_description='
            '"say \\"hi\\" \\\\ bye"',
            bearer_challenge('say "hi" \\ bye'),
        )

    def test_control_and_non_ascii_characters_become_spaces(self):
        value = bearer_challenge("a\r\nb\tc")
        for forbidden in ("\r", "\n", "\t"):
            self.assertNotIn(forbidden, value)
        self.assertEqual(
            'Bearer error="invalid_token", error_description="a  b c"', value
        )
        self.assertTrue(bearer_challenge("café").isascii())

    def test_header_injection_is_not_possible(self):
        value = bearer_challenge('x"\r\nSet-Cookie: a=b')
        self.assertNotIn("\r", value)
        self.assertNotIn("\n", value)
        self.assertEqual('x"  Set-Cookie: a=b', unquote_description(value))

    def test_invalid_token_exception(self):
        error = InvalidToken("msg")
        self.assertEqual(401, error.status_code)
        self.assertIsInstance(error, InvalidCredentials)
        self.assertIsInstance(error, InvalidUsage)
        self.assertEqual({"error": "msg"}, error.to_dict())
        self.assertEqual(bearer_challenge("msg"), error.headers[CHALLENGE_HEADER])

    def test_invalid_token_default_message(self):
        error = InvalidToken()
        self.assertEqual("Invalid token", error.error)
        self.assertEqual(401, error.status_code)
        self.assertEqual(
            bearer_challenge("Invalid token"), error.headers[CHALLENGE_HEADER]
        )

    def test_other_exceptions_carry_no_headers(self):
        self.assertEqual({}, InvalidUsage("x").headers)
        self.assertEqual({}, InvalidCredentials("x", status_code=400).headers)

    def test_invalid_usage_keeps_the_given_headers(self):
        given = {"X-Test": "1"}
        error = InvalidUsage("x", status_code=418, headers=given)
        self.assertEqual({"X-Test": "1"}, error.headers)
        self.assertIsNot(given, error.headers)


class TokenSupport:
    """Container (so that unittest does not collect the base)."""

    class Base(SecurityLevelTestMixin, TestCase):
        security_level = 1
        config_overrides = {"MFA_REQUIRED": 0}

        def setUp(self):
            db.create_all()
            access_init_command(verbose=False)
            register_deployed_dags_command_test(verbose=False)
            self.user = UserModel(
                data={
                    "username": "ana",
                    "email": "ana@test.com",
                    "password": STRONG_PASSWORD,
                }
            )
            self.user.save()
            UserRoleModel({"user_id": self.user.id, "role_id": PLANNER_ROLE}).save()

        def tearDown(self):
            db.session.remove()
            db.drop_all()

        # -- helpers -----------------------------------------------------

        def assert_invalid_token(self, response, message=None):
            self.assertEqual(401, response.status_code, response.json)
            self.assertIn(CHALLENGE_HEADER, response.headers)
            value = response.headers[CHALLENGE_HEADER]
            self.assertTrue(value.startswith(CHALLENGE_PREFIX), value)
            self.assertTrue(value.endswith('"'), value)
            self.assertNotIn("\n", value)
            self.assertNotIn("\r", value)
            description = unquote_description(value)
            self.assertEqual(response.json["error"], description)
            if message is not None:
                self.assertEqual(message, description)

        def assert_no_challenge(self, response, status):
            self.assertEqual(status, response.status_code, response.json)
            self.assertNotIn(CHALLENGE_HEADER, response.headers)

        def internal_token(self, key=None, **claims):
            payload = {
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "sub": "ana",
                "iss": INTERNAL_TOKEN_ISSUER,
                "tv": self.user.token_version or 0,
            }
            payload.update(claims)
            return jwt.encode(
                payload, key or current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
            )

        def login_token(self):
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps({"username": "ana", "password": STRONG_PASSWORD}),
                headers=JSON_HEADER,
            )
            self.assertEqual(200, response.status_code, response.json)
            return response.json["token"]

        def get(self, url, token):
            return self.client.get(url, headers=auth_header(token))

        def get_instances(self, token):
            return self.get(INSTANCE_URL, token)

        def new_session(self):
            return SessionModel.create_for_user(self.user)

        def refresh(self, refresh_token):
            return self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": refresh_token}),
                headers=JSON_HEADER,
            )


class InvalidTokenCases:
    class Base(TokenSupport.Base):
        # -- 401 with the challenge (criteria 1 to 6) ----------------------

        def test_control_valid_token_is_accepted(self):
            self.assertEqual(200, self.get_instances(self.login_token()).status_code)

        def test_expired_token(self):
            token = self.internal_token(
                exp=datetime.now(timezone.utc) - timedelta(hours=1),
                iat=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            self.assert_invalid_token(self.get_instances(token), MSG_EXPIRED)

        def test_malformed_tokens(self):
            for token in ("abc.def.ghi", "abcdef"):
                with self.subTest(token=token):
                    response = self.get_instances(token)
                    self.assert_invalid_token(response, MSG_FORMAT)
                    for leak in ("jwt", "Error", "Traceback"):
                        self.assertNotIn(leak, response.json["error"])

        def test_tampered_signature(self):
            token = self.login_token()
            head, body, signature = token.split(".")
            index = len(signature) // 2
            replacement = "A" if signature[index] != "A" else "B"
            tampered = ".".join(
                [head, body, signature[:index] + replacement + signature[index + 1 :]]
            )
            self.assertNotEqual(token, tampered)
            self.assert_invalid_token(self.get_instances(tampered), MSG_FORMAT)

        def test_token_signed_with_another_key(self):
            token = self.internal_token(key="another-secret-key-of-at-least-32-bytes")
            self.assert_invalid_token(self.get_instances(token), MSG_FORMAT)

        def test_wrong_issuer(self):
            token = self.internal_token(iss="other")
            self.assert_invalid_token(self.get_instances(token), MSG_FORMAT)

        def test_stale_token_version(self):
            token = self.login_token()
            user = UserModel.get_one_object(username="ana")
            user.revoke_all_sessions()
            db.session.commit()
            self.assert_invalid_token(self.get_instances(token), MSG_REVOKED)

        def test_closed_session(self):
            session = self.new_session()
            token = Auth.generate_access_token(self.user.id, session=session)
            self.assertEqual(200, self.get_instances(token).status_code)
            session.revoke()
            self.assert_invalid_token(self.get_instances(token), MSG_CLOSED)

        def test_session_past_its_absolute_lifetime(self):
            session = self.new_session()
            token = Auth.generate_access_token(self.user.id, session=session)
            session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.session.add(session)
            db.session.commit()
            self.assert_invalid_token(self.get_instances(token), MSG_SESSION_EXPIRED)

        def test_revoked_api_key(self):
            key = Auth.generate_api_key(self.user.id)
            self.assertEqual(200, self.get_instances(key).status_code)
            self.user.revoke_api_keys()
            self.assert_invalid_token(self.get_instances(key), MSG_API_KEY)

        def test_deleted_user_token(self):
            token = self.login_token()
            UserModel.get_one_object(username="ana").delete()
            self.assert_invalid_token(self.get_instances(token), MSG_NO_USER)

        def test_token_of_an_unknown_user(self):
            token = self.internal_token(sub="ghost")
            self.assert_invalid_token(self.get_instances(token), MSG_NO_USER)

        def test_refresh_token_on_normal_endpoint(self):
            session = self.new_session()
            refresh_token = Auth.generate_refresh_token(self.user.id, session)
            for url in (INSTANCE_URL, SCHEMA_URL):
                with self.subTest(url=url):
                    self.assert_invalid_token(
                        self.get(url, refresh_token), MSG_REFRESH_ON_ENDPOINT
                    )

        def test_refresh_endpoint_rejects_bad_tokens(self):
            # malformed
            self.assert_invalid_token(self.refresh("abc.def.ghi"), MSG_FORMAT)
            # an access token is not a refresh token
            self.assert_invalid_token(
                self.refresh(self.login_token()), "Invalid refresh token"
            )
            # session closed with the logout
            session = self.new_session()
            refresh_token = Auth.generate_refresh_token(self.user.id, session)
            logout = self.client.post(
                LOGOUT_URL,
                data=json.dumps({"refresh_token": refresh_token}),
                headers=JSON_HEADER,
            )
            self.assertEqual(200, logout.status_code)
            self.assert_invalid_token(
                self.refresh(refresh_token),
                "The session is no longer valid, please log in again",
            )

        def test_refresh_token_reuse(self):
            session = self.new_session()
            session_id = session.session_id
            first = Auth.generate_refresh_token(self.user.id, session)
            rotated = self.refresh(first)
            self.assertEqual(200, rotated.status_code, rotated.json)
            replay = self.refresh(first)
            self.assert_invalid_token(replay, MSG_REVOKED)
            db.session.expire_all()
            self.assertIsNone(SessionModel.get_active(session_id))

        def test_stale_refresh_token_version(self):
            session = self.new_session()
            refresh_token = Auth.generate_refresh_token(self.user.id, session)
            user = UserModel.get_one_object(username="ana")
            user.revoke_all_sessions()
            db.session.commit()
            self.assert_invalid_token(self.refresh(refresh_token), MSG_REVOKED)

        def test_refresh_token_of_an_unknown_user(self):
            session = self.new_session()
            refresh_token = Auth.generate_refresh_token(self.user.id, session)
            ghost = jwt.decode(
                refresh_token,
                current_app.config["SECRET_TOKEN_KEY"],
                algorithms=["HS256"],
            )
            ghost["sub"] = "ghost"
            forged = jwt.encode(
                ghost, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
            )
            self.assert_invalid_token(self.refresh(forged), "Invalid refresh token")

        # -- the same stays the same, without the challenge (7 to 10) --------

        def test_missing_or_malformed_header_is_400(self):
            token = self.login_token()
            cases = {
                "no header": JSON_HEADER,
                "other scheme": {**JSON_HEADER, "Authorization": "Token abc"},
                "glued": {**JSON_HEADER, "Authorization": "Bearer" + token},
                "empty token": {**JSON_HEADER, "Authorization": "Bearer "},
            }
            for label, headers in cases.items():
                with self.subTest(case=label):
                    response = self.client.get(INSTANCE_URL, headers=headers)
                    self.assert_no_challenge(response, 400)

        def test_refresh_without_token_is_400(self):
            response = self.client.post(
                REFRESH_URL, data=json.dumps({}), headers=JSON_HEADER
            )
            self.assert_no_challenge(response, 400)

        def test_failed_login_is_400(self):
            wrong_password = self.client.post(
                LOGIN_URL,
                data=json.dumps({"username": "ana", "password": "Wrong#Pass9x!"}),
                headers=JSON_HEADER,
            )
            unknown_user = self.client.post(
                LOGIN_URL,
                data=json.dumps({"username": "nobody", "password": "Wrong#Pass9x!"}),
                headers=JSON_HEADER,
            )
            self.assert_no_challenge(wrong_password, 400)
            self.assert_no_challenge(unknown_user, 400)
            self.assertEqual(wrong_password.json["error"], unknown_user.json["error"])

        def test_forbidden_is_403_without_challenge(self):
            purpose = Auth.generate_token(self.user.id, purpose=TOKEN_PURPOSE_PWD_RESET)
            response = self.get_instances(purpose)
            self.assert_no_challenge(response, 403)
            self.assertEqual("purpose_token", response.json.get("error_code"))

            key = Auth.generate_api_key(self.user.id)
            response = self.client.put(
                f"{USER_URL}{self.user.id}/",
                data=json.dumps({"first_name": "Ana"}),
                headers=auth_header(key),
            )
            self.assert_no_challenge(response, 403)
            self.assertEqual("api_key_forbidden", response.json.get("error_code"))

            response = self.get(USER_URL, self.login_token())
            self.assert_no_challenge(response, 403)

        def test_unexpected_decode_error_is_500(self):
            token = self.login_token()
            with mock.patch(
                "cornflow.shared.authentication.auth.jwt.decode",
                side_effect=RuntimeError("boom"),
            ):
                response = self.get_instances(token)
            self.assert_no_challenge(response, 500)

        def test_token_check_endpoint_unchanged(self):
            response = self.client.get(TOKEN_URL, headers=auth_header("abc.def.ghi"))
            self.assertEqual(200, response.status_code)
            self.assertEqual(0, response.json["valid"])
            logout = self.client.post(
                LOGOUT_URL,
                data=json.dumps({"refresh_token": "abc.def.ghi"}),
                headers=JSON_HEADER,
            )
            self.assertEqual(200, logout.status_code)


class TestInvalidTokenLevel1(InvalidTokenCases.Base):
    security_level = 1


class TestInvalidTokenLevel2(InvalidTokenCases.Base):
    security_level = 2


class TestInvalidTokenLevel3(InvalidTokenCases.Base):
    security_level = 3


# -- BI token ---------------------------------------------------------------


class BITokenCases:
    class Base(TokenSupport.Base):
        """Only this class registers the BI test route."""

        def create_app(self):
            app = super().create_app()

            def view():
                user = BIAuth().get_user_from_header(request.headers)
                return {"id": user.id}

            app.add_url_rule(BI_TEST_URL, "test_bi_auth", view)
            return app

        def bi_token(self, key=None, **claims):
            payload = {
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "sub": "ana",
            }
            payload.update(claims)
            return jwt.encode(
                payload, key or current_app.config["SECRET_BI_KEY"], algorithm="HS256"
            )

        def expired_bi_token(self):
            return self.bi_token(exp=datetime.now(timezone.utc) - timedelta(hours=1))

        def invalid_bi_token(self):
            return self.bi_token(key="another-secret-key-of-at-least-32-bytes")

        def test_bi_decode_raises_invalid_token(self):
            cases = {
                self.expired_bi_token(): MSG_BI_EXPIRED,
                self.invalid_bi_token(): MSG_BI_INVALID,
            }
            for token, message in cases.items():
                with self.subTest(message=message):
                    with self.assertRaises(InvalidToken) as ctx:
                        BIAuth.decode_token(token)
                    self.assertEqual(401, ctx.exception.status_code)
                    self.assertEqual(message, ctx.exception.error)
                    self.assertEqual(
                        bearer_challenge(message),
                        ctx.exception.headers[CHALLENGE_HEADER],
                    )

        def test_bi_decode_without_token_is_400(self):
            for token in ("", None):
                with self.subTest(token=token):
                    with self.assertRaises(InvalidCredentials) as ctx:
                        BIAuth.decode_token(token)
                    self.assertNotIsInstance(ctx.exception, InvalidToken)
                    self.assertEqual(400, ctx.exception.status_code)
                    self.assertNotIn(CHALLENGE_HEADER, ctx.exception.headers)

        def test_bi_http_response(self):
            response = self.get(BI_TEST_URL, self.bi_token())
            self.assertEqual(200, response.status_code, response.json)
            self.assertEqual(self.user.id, response.json["id"])
            self.assert_invalid_token(
                self.get(BI_TEST_URL, self.expired_bi_token()), MSG_BI_EXPIRED
            )
            self.assert_invalid_token(
                self.get(BI_TEST_URL, self.invalid_bi_token()), MSG_BI_INVALID
            )

        def test_bi_http_without_token_is_400(self):
            response = self.client.get(BI_TEST_URL, headers=JSON_HEADER)
            self.assert_no_challenge(response, 400)


class TestBITokenLevel1(BITokenCases.Base):
    security_level = 1


class TestBITokenLevel2(BITokenCases.Base):
    security_level = 2


class TestBITokenLevel3(BITokenCases.Base):
    security_level = 3


# -- OIDC -------------------------------------------------------------------

OID_PROVIDER = "https://test-provider.example.com"
OID_AUDIENCE = "test-audience-id"


def _rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class OidcInvalidTokenCases:
    class Base(TokenSupport.Base):
        security_level = 1
        config_overrides = {
            "MFA_REQUIRED": 0,
            "AUTH_TYPE": AUTH_OID,
            "OID_PROVIDER": OID_PROVIDER,
            "OID_EXPECTED_AUDIENCE": OID_AUDIENCE,
        }

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.private_key = _rsa_key()
            cls.other_private_key = _rsa_key()

        def setUp(self):
            db.create_all()
            access_init_command(verbose=False)
            register_deployed_dags_command_test(verbose=False)
            self.user = UserModel(
                data={
                    "username": "ana",
                    "email": "ana@test.com",
                    "password": STRONG_PASSWORD,
                }
            )
            self.user.save()
            UserRoleModel({"user_id": self.user.id, "role_id": PLANNER_ROLE}).save()
            public_keys_cache.clear()
            patcher = mock.patch.object(
                Auth,
                "get_public_keys",
                return_value={"kid-1": self.private_key.public_key()},
            )
            self.mock_keys = patcher.start()
            self.addCleanup(patcher.stop)

        def tearDown(self):
            public_keys_cache.clear()
            db.session.remove()
            db.drop_all()

        def oidc_token(self, key=None, kid="kid-1", **claims):
            payload = {
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iat": datetime.now(timezone.utc),
                "sub": "ana",
                "iss": OID_PROVIDER,
                "aud": OID_AUDIENCE,
            }
            payload.update(claims)
            return jwt.encode(
                payload,
                key or self.private_key,
                algorithm="RS256",
                headers={"kid": kid},
            )

        def expired_token(self):
            return self.oidc_token(
                exp=datetime.now(timezone.utc) - timedelta(hours=1),
                iat=datetime.now(timezone.utc) - timedelta(hours=2),
            )

        def test_control_valid_token(self):
            response = self.get_instances(self.oidc_token())
            self.assertEqual(200, response.status_code, response.json)

        def test_expired_token(self):
            self.assert_invalid_token(
                self.get_instances(self.expired_token()), MSG_EXPIRED
            )

        def test_signed_with_another_key(self):
            token = self.oidc_token(key=self.other_private_key)
            self.assert_invalid_token(self.get_instances(token), MSG_FORMAT_OIDC)

        def test_unknown_kid(self):
            token = self.oidc_token(kid="kid-unknown")
            self.assert_invalid_token(self.get_instances(token), MSG_FORMAT_OIDC)

        def test_wrong_audience(self):
            token = self.oidc_token(aud="another-audience")
            self.assert_invalid_token(self.get_instances(token), MSG_FORMAT_OIDC)

        def test_keys_cannot_be_fetched(self):
            self.mock_keys.side_effect = CommunicationError(
                "Failed to fetch public keys from authentication provider",
                log_txt="no network in the tests",
                status_code=400,
            )
            self.assert_invalid_token(
                self.get_instances(self.oidc_token()), MSG_FORMAT_OIDC
            )

        def test_login_with_an_expired_token(self):
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps({}),
                headers=auth_header(self.expired_token()),
            )
            self.assert_invalid_token(response, MSG_EXPIRED)

        def test_login_without_header_is_400(self):
            response = self.client.post(
                LOGIN_URL, data=json.dumps({}), headers=JSON_HEADER
            )
            self.assertEqual(400, response.status_code)
            self.assertNotIn(CHALLENGE_HEADER, response.headers)


class TestOidcInvalidTokenLevel1(OidcInvalidTokenCases.Base):
    security_level = 1


class TestOidcInvalidTokenLevel2(OidcInvalidTokenCases.Base):
    security_level = 2


class TestOidcInvalidTokenLevel3(OidcInvalidTokenCases.Base):
    security_level = 3


if __name__ == "__main__":
    unittest.main()
