"""
Unit test for the log in endpoint
"""

import json
import logging as log
from unittest import mock
import requests
import jwt
from datetime import datetime, timedelta

from flask import current_app


from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.shared.const import SERVICE_ROLE, INTERNAL_TOKEN_ISSUER, AUTH_OID
from cornflow.tests.const import LOGIN_URL
from cornflow.tests.custom_test_case import CustomTestCase, LoginTestCases


class TestLogIn(LoginTestCases.LoginEndpoint):
    def setUp(self):
        super().setUp()
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }
        user = UserModel(data=self.data)
        user.save()
        db.session.commit()
        # we take out the email, we do not need it to log in
        self.data.pop("email")
        self.idx = UserModel.query.filter_by(username="testname").first().id

    def test_successful_log_in(self):
        """
        Test the successful log in
        """
        super().test_successful_log_in()
        self.assertEqual(self.idx, self.response.json["id"])

    @mock.patch("cornflow.endpoints.login.Auth.generate_token")
    def test_exception_on_token_generation(self, mock_generate_token):
        # Simulate an exception when generate_token is called
        mock_generate_token.side_effect = Exception("Custom exception")

        # Prepare login payload
        payload = self.data

        # Make a login request
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        # Assert that the response is a 400 error
        self.assertEqual(400, response.status_code)
        # Assert that the error message contains the expected text
        self.assertIn("Error in generating user token", response.json["error"])


class TestLogInOpenAuth(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        test_user = UserModel(data=self.user_data)
        test_user.save()

        self.user_data.pop("email")
        self.test_user_id = test_user.id

        # Setup service user
        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.service_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            response.json["error"],
            "Must provide a token in Authorization header. Cannot log in with username and password",
        )

    @mock.patch("cornflow.shared.authentication.auth.Auth.get_public_keys")
    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_kid_not_in_public_keys(self, mock_jwt, mock_get_public_keys):
        """
        Tests token validation failure when the kid is not found in public keys
        """
        # Import the real exceptions to ensure they are preserved
        from jwt.exceptions import (
            InvalidTokenError,
            ExpiredSignatureError,
            InvalidIssuerError,
            InvalidSignatureError,
            DecodeError,
        )

        # Keep the real exception classes in the mock
        mock_jwt.ExpiredSignatureError = ExpiredSignatureError
        mock_jwt.InvalidTokenError = InvalidTokenError
        mock_jwt.InvalidIssuerError = InvalidIssuerError
        mock_jwt.InvalidSignatureError = InvalidSignatureError
        mock_jwt.DecodeError = DecodeError

        mock_jwt.get_unverified_header.return_value = {"kid": "test_kid"}

        # Mock jwt.decode to return different results based on arguments
        def decode_side_effect(*args, **kwargs):
            if kwargs.get("options", {}).get("verify_signature") is False:
                return {"iss": current_app.config.get("OID_PROVIDER", "valid_issuer")}
            raise InvalidTokenError("Invalid token")

        mock_jwt.decode.side_effect = decode_side_effect

        # Mock get_public_keys to return keys that don't contain our kid
        mock_get_public_keys.return_value = {"different_kid": "some_key"}

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            response.json["error"], "Invalid token format, signature, or configuration"
        )

    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_missing_kid_in_token(self, mock_jwt):
        """
        Tests token validation failure when the token header is missing the kid
        """
        # Import the real exceptions to ensure they are preserved
        from jwt.exceptions import (
            InvalidTokenError,
            ExpiredSignatureError,
            InvalidIssuerError,
            InvalidSignatureError,
            DecodeError,
        )

        # Keep the real exception classes in the mock
        mock_jwt.ExpiredSignatureError = ExpiredSignatureError
        mock_jwt.InvalidTokenError = InvalidTokenError
        mock_jwt.InvalidIssuerError = InvalidIssuerError
        mock_jwt.InvalidSignatureError = InvalidSignatureError
        mock_jwt.DecodeError = DecodeError

        # Mock jwt.get_unverified_header to return a header without kid
        mock_jwt.get_unverified_header.return_value = {"alg": "RS256"}

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "Invalid token format, signature, or configuration", response.json["error"]
        )

    @mock.patch("cornflow.shared.authentication.auth.requests.get")
    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_public_keys_fetch_fail(self, mock_jwt, mock_get):
        """
        Tests failure when trying to fetch public keys from the OIDC provider
        """
        # Import the real exceptions to ensure they are preserved
        from jwt.exceptions import (
            InvalidTokenError,
            ExpiredSignatureError,
            InvalidIssuerError,
            InvalidSignatureError,
            DecodeError,
        )

        # Keep the real exception classes in the mock
        mock_jwt.ExpiredSignatureError = ExpiredSignatureError
        mock_jwt.InvalidTokenError = InvalidTokenError
        mock_jwt.InvalidIssuerError = InvalidIssuerError
        mock_jwt.InvalidSignatureError = InvalidSignatureError
        mock_jwt.DecodeError = DecodeError

        # Clear the cache
        from cornflow.shared.authentication.auth import public_keys_cache

        public_keys_cache.clear()

        # Mock jwt to pass initial validation
        mock_jwt.get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt.decode.side_effect = lambda *args, **kwargs: (
            {"iss": current_app.config["OID_PROVIDER"]}
            if kwargs.get("options", {}).get("verify_signature") is False
            else {}
        )

        # Mock get to fail
        mock_get.side_effect = requests.exceptions.RequestException(
            "Failed to get keys"
        )

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "Invalid token format, signature, or configuration",
            response.json["error"],
        )

    @mock.patch("cornflow.shared.authentication.Auth.decode_token")
    def test_service_user_login_no_fail(self, mock_decode):
        """
        Tests successful login for an existing service user with valid token
        """
        mock_decode.return_value = {"sub": "service_user"}
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id, response.json["id"])

    @mock.patch("cornflow.shared.authentication.Auth.decode_token")
    def test_new_user_login_no_fail(self, mock_decode):
        """
        Tests successful login and creation of a new user with valid token
        """
        mock_decode.return_value = {"sub": "test_user"}
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id + 1, response.json["id"])

    @mock.patch("cornflow.shared.authentication.Auth.verify_token")
    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_public_keys_caching(self, mock_jwt, mock_verify_token):
        """
        Tests that public keys are cached and reused for subsequent requests.
        Also verifies that when a new kid is encountered that's not in the cache,
        the system fetches fresh keys from the provider.
        """
        # Import the real exceptions to ensure they are preserved
        from jwt.exceptions import (
            InvalidTokenError,
            ExpiredSignatureError,
            InvalidIssuerError,
            InvalidSignatureError,
            DecodeError,
        )

        # Keep the real exception classes in the mock
        mock_jwt.ExpiredSignatureError = ExpiredSignatureError
        mock_jwt.InvalidTokenError = InvalidTokenError
        mock_jwt.InvalidIssuerError = InvalidIssuerError
        mock_jwt.InvalidSignatureError = InvalidSignatureError
        mock_jwt.DecodeError = DecodeError

        # Mock jwt to return valid unverified header and payload
        mock_jwt.get_unverified_header.return_value = {"kid": "test_kid"}
        mock_jwt.decode.side_effect = lambda *args, **kwargs: (
            {"iss": current_app.config["OID_PROVIDER"]}
            if kwargs.get("options", {}).get("verify_signature") is False
            else {"sub": "test_user", "email": "test_user@test.com"}
        )

        # Mock verify_token to always return a valid token payload
        mock_verify_token.return_value = {
            "sub": "test_user",
            "email": "test_user@test.com",
        }

        # Make first request
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(200, response.status_code)

        # Make second request
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_token",
            },
        )

        self.assertEqual(200, response.status_code)

        # Verify token was verified twice
        self.assertEqual(2, mock_verify_token.call_count)

        # Now test with a different token
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer some_different_token",
            },
        )

        self.assertEqual(200, response.status_code)

        # Verify token was verified a third time
        self.assertEqual(3, mock_verify_token.call_count)

    def test_old_token(self):
        """
        Tests using an expired token.
        """
        # Generate an expired token
        payload = {
            # Token expired 1 hour ago
            "exp": datetime.utcnow() - timedelta(hours=1),
            # Token created 2 hours ago
            "iat": datetime.utcnow() - timedelta(hours=2),
            "sub": "testname",
            "iss": INTERNAL_TOKEN_ISSUER,
        }

        expired_token = jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {expired_token}",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "The token has expired, please login again", response.json["error"]
        )

    def test_missing_auth_header(self):
        """
        Tests that missing Authorization header raises proper error
        """
        response = self.client.post(
            LOGIN_URL, data=json.dumps({}), headers={"Content-Type": "application/json"}
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Authorization header is missing")

    def test_invalid_auth_header(self):
        """
        Tests that malformed Authorization header raises proper error
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Invalid Format",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "Invalid Authorization header format. Must be 'Bearer <token>'",
            response.json["error"],
        )


class TestLogInOpenAuthService(CustomTestCase):

    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 1
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        test_user = UserModel(data=self.user_data)
        test_user.save()

        self.user_data.pop("email")

        self.test_user_id = test_user.id

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.service_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id, response.json["id"])

    def test_no_credentials_error(self):
        """
        Tests that a user can not log in without token or username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Authorization header is missing")

    def test_other_user_password(self):
        """
        Tests that a user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.user_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Invalid request")

    @mock.patch("cornflow.shared.authentication.Auth.decode_token")
    def test_token_login(self, mock_decode):
        """
        Tests that a user can successfully log in with a valid token
        """
        mock_decode.return_value = {"sub": "testname"}

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer valid_token",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.test_user_id, response.json["id"])

    def test_invalid_token_login(self):
        """
        Tests that login fails with an invalid token
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            response.json["error"], "Invalid token format, signature, or configuration"
        )
