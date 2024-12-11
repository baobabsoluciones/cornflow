"""
Unit test for the log in endpoint.

This module contains test cases for the login functionality, verifying
user authentication and response handling.

Classes
-------
TestLogIn
    Test cases for user login functionality.
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import LoginTestCases


class TestLogIn(LoginTestCases.LoginEndpoint):
    """
    Test cases for user login functionality.

    This class extends LoginTestCases.LoginEndpoint to test specific login scenarios
    and verify user authentication behavior.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Creates a test user in the database and prepares login credentials.
        The setup includes:
        - Creating database tables
        - Setting authentication type
        - Creating a test user
        - Preparing login data
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
        # we take out the email, we do not need it to log in
        self.data.pop("email")
        self.idx = UserModel.query.filter_by(username="testname").first().id

    def test_successful_log_in(self):
        """
        Tests successful user login.

        Verifies that:
        - The login is successful (checked in parent class)
        - The returned user ID matches the expected user
        """
        super().test_successful_log_in()
        self.assertEqual(self.idx, self.response.json["id"])
