"""
Unit test for the sign up functionality.

This module contains test cases for user registration functionality,
ensuring proper user account creation and validation.

Classes
-------
TestSignUp
    Test cases for user registration functionality
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase


class TestSignUp(CustomTestCase):
    """
    Test cases for the sign up functionality.

    This class tests user registration scenarios, including successful registration,
    validation of user data, and handling of invalid registration attempts.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Authentication configuration
        - Test user data
        """
        super().setUp()
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

    def test_successful_sign_up(self):
        """
        Tests successful user registration.

        Verifies that:
        - A new user can be created with valid data
        - The response contains the expected user information
        - The user is properly stored in the database
        """
        response = self.client.post(
            "/signup/",
            data=self.data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(str, type(response.json["token"]))
        user = UserModel.query.filter_by(username=self.data["username"]).first()
        self.assertIsNotNone(user)

    def test_duplicate_username(self):
        """
        Tests registration with duplicate username.

        Verifies that:
        - Registration fails with duplicate username
        - Appropriate error message is returned
        - Status code indicates conflict
        """
        # First registration
        self.client.post(
            "/signup/",
            data=self.data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        # Second registration with same username
        response = self.client.post(
            "/signup/",
            data=self.data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(409, response.status_code)
        self.assertEqual(str, type(response.json["error"]))

    def test_invalid_email(self):
        """
        Tests registration with invalid email format.

        Verifies that:
        - Registration fails with invalid email format
        - Appropriate validation error is returned
        - Status code indicates bad request
        """
        self.data["email"] = "invalid_email"
        response = self.client.post(
            "/signup/",
            data=self.data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))

    def test_missing_required_fields(self):
        """
        Tests registration with missing required fields.

        Verifies that:
        - Registration fails when required fields are missing
        - Appropriate error messages are returned for each missing field
        - Status code indicates bad request
        """
        invalid_data = {}
        response = self.client.post(
            "/signup/",
            data=invalid_data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))
