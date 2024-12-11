"""
Unit test for the health check endpoint.

This module contains test cases for the health check endpoint, which verifies
the application's operational status.

Classes
-------
TestHealth
    Test cases for health check endpoint functionality
"""

# Import from libraries
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.shared import db


class TestHealth(TestCase):
    """
    Test cases for the health check endpoint.

    This class verifies that the application's health check endpoint
    responds correctly and indicates proper system operation.
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

        Creates necessary database tables for testing.
        """
        db.create_all()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Removes all database tables and session data.
        """
        db.session.remove()
        db.drop_all()

    def test_health(self):
        """
        Tests the health check endpoint.

        Verifies that:
        - The endpoint returns a 200 status code
        - The response contains the expected health status message
        """
        response = self.client.get("/health/")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok"}, response.json)
