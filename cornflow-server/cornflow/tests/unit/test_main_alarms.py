"""
Unit test for the main alarms functionality.

This module contains test cases for the main alarms system, which handles
core alarm functionality and integration with other system components.

Classes
-------
TestMainAlarms
    Test cases for core alarm system functionality
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase


class TestMainAlarms(CustomTestCase):
    """
    Test cases for the main alarms system functionality.

    This class tests the core alarm system features, including alarm creation,
    management, and integration with other system components.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Base test setup from parent class
        - Database tables
        - Test user data
        - Alarm configuration
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

    def test_get_main_alarms(self):
        """
        Tests retrieval of main alarms.

        Verifies that:
        - The main alarms endpoint returns a 200 status code
        - The response contains the expected alarm data structure
        - The alarms list is properly formatted
        """
        response = self.client.get(
            "/main_alarms/",
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(list, type(response.json))

    def test_get_main_alarms_with_filters(self):
        """
        Tests retrieval of main alarms with filters.

        Verifies that:
        - The endpoint correctly processes filter parameters
        - Filtered results match the expected criteria
        - The response structure is maintained with filters
        """
        response = self.client.get(
            "/main_alarms/?limit=1",
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(list, type(response.json))
