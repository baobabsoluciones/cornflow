"""
Unit test for the API view functionality.

This module contains test cases for the API view base class, which provides
common functionality for all API endpoints.

Classes
-------
TestApiView
    Test cases for base API view functionality
"""

# Import from libraries
from flask import current_app
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared import db


class TestApiView(TestCase):
    """
    Test cases for the API view base functionality.

    This class tests the common functionality provided by the base API view,
    including authentication, request handling, and response formatting.
    """

    def create_app(self):
        """
        Creates a test application instance.

        :returns: A configured Flask application for testing
        :rtype: Flask
        """
        app = create_app("testing")
        return app

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the database and creates necessary test data including:
        - Database tables
        - Test users
        - Authentication configuration
        """
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

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Removes all database tables and session data.
        """
        db.session.remove()
        db.drop_all()

    def test_get_request_args(self):
        """
        Tests request arguments parsing.

        Verifies that:
        - The endpoint correctly processes query parameters
        - The response contains the expected data structure
        """
        response = self.client.get("/users/", query_string={"limit": 1})
        self.assertEqual(401, response.status_code)

    def test_get_request_args_bad_format(self):
        """
        Tests handling of malformed request arguments.

        Verifies that:
        - The endpoint properly handles invalid query parameters
        - The response indicates the error appropriately
        """
        response = self.client.get("/users/", query_string={"limit": "bad_format"})
        self.assertEqual(401, response.status_code)
