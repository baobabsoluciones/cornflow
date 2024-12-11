"""
Unit test for token functionality.

This module contains test cases for authentication token handling, including
token generation, validation, and expiration checks.

Classes
-------
TestToken
    Test cases for authentication token functionality
"""

# Import from libraries
from flask import current_app
import jwt
from datetime import datetime, timedelta

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CheckTokenTestCase


class TestToken(CheckTokenTestCase.TokenEndpoint):
    """
    Test cases for authentication token functionality.

    This class tests the token-based authentication system, including token
    generation, validation, expiration, and error handling.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Test user
        - Authentication configuration
        """
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

    def test_valid_token(self):
        """
        Tests validation of a valid token.

        Verifies that:
        - A valid token is properly validated
        - Token payload contains expected user information
        - Token expiration is correctly handled
        """
        payload = {
            "sub": 1,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        self.token = jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )
        self.get_check_token()
        self.assertEqual(200, self.response.status_code)

    def test_expired_token(self):
        """
        Tests handling of expired tokens.

        Verifies that:
        - Expired tokens are properly detected
        - Appropriate error response is returned
        - Status code indicates token expiration
        """
        payload = {
            "sub": 1,
            "iat": datetime.utcnow() - timedelta(days=2),
            "exp": datetime.utcnow() - timedelta(days=1),
        }
        self.token = jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )
        self.get_check_token()
        self.assertEqual(400, self.response.status_code)
        self.assertEqual(
            "The token has expired, please login again", self.response.json["error"]
        )

    def test_invalid_token(self):
        """
        Tests handling of invalid tokens.

        Verifies that:
        - Invalid tokens are properly detected
        - Appropriate error response is returned
        - Status code indicates token invalidity
        """
        self.token = "invalid_token"
        self.get_check_token()
        self.assertEqual(400, self.response.status_code)
        self.assertEqual(
            "Invalid token, please try again with a new token",
            self.response.json["error"],
        )

    def test_missing_token(self):
        """
        Tests requests without tokens.

        Verifies that:
        - Requests without tokens are properly handled
        - Appropriate error response is returned
        - Status code indicates missing authentication
        """
        self.token = None
        self.get_check_token()
        self.assertEqual(401, self.response.status_code)
        self.assertEqual("Token is missing", self.response.json["error"])
