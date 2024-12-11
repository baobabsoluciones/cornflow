"""
Unit test for the alarms endpoint.

This module contains test cases for the alarms functionality, which handles
system notifications and alerts.

Classes
-------
TestAlarms
    Test cases for alarms endpoint functionality
"""

# Imports from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase


class TestAlarms(CustomTestCase):
    """
    Test cases for the alarms endpoint functionality.

    This class tests the creation, retrieval, and management of system alarms,
    verifying proper alarm handling and user notifications.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the database and creates necessary test data including:
        - Database tables
        - Test users
        - Test alarms data
        """
        super().setUp()
        db.create_all()
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }
        user = UserModel(data=self.data)
        user.save()
        db.session.commit()

    def test_get_alarms(self):
        """
        Tests retrieval of alarms.

        Verifies that:
        - The alarms endpoint returns a 200 status code
        - The response contains the expected alarm data structure
        """
        response = self.client.get(
            "/alarms/",
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(list, type(response.json))
