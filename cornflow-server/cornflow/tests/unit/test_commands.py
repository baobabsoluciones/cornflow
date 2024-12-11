"""
Unit tests for command functionality.

This module contains test cases for command operations, including
command execution, validation, and error handling.

Classes
-------
TestCommands
    Test cases for command operations and handling
"""

# Import from libraries
import unittest

# Import from internal modules
from cornflow.commands import create_admin_user, create_service_user, create_viewer_user
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.shared.exceptions import InvalidCredentials


class TestCommands(unittest.TestCase):
    """
    Test cases for command functionality.

    This class tests various command operations including user creation,
    role assignment, and error handling for invalid inputs.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Database tables
        - Test data
        - Required configurations
        """
        db.create_all()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Performs:
        - Database cleanup
        - Session removal
        """
        db.session.remove()
        db.drop_all()

    def test_create_admin_user(self):
        """
        Tests admin user creation command.

        Verifies that:
        - Admin users can be created with valid credentials
        - Admin privileges are correctly assigned
        - User data is properly stored
        """
        create_admin_user("admin", "admin@test.com", "Adminpass1!")
        user = UserModel.query.filter_by(username="admin").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "admin@test.com")
        self.assertTrue(user.is_admin)

    def test_create_service_user(self):
        """
        Tests service user creation command.

        Verifies that:
        - Service users can be created
        - Service role is properly assigned
        - User data is correctly stored
        """
        create_service_user("service", "service@test.com", "Servicepass1!")
        user = UserModel.query.filter_by(username="service").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "service@test.com")
        self.assertTrue(user.is_service_user())

    def test_create_viewer_user(self):
        """
        Tests viewer user creation command.

        Verifies that:
        - Viewer users can be created
        - Viewer role is properly assigned
        - User data is correctly stored
        """
        create_viewer_user("viewer", "viewer@test.com", "Viewerpass1!")
        user = UserModel.query.filter_by(username="viewer").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "viewer@test.com")
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_service_user())

    def test_invalid_credentials(self):
        """
        Tests error handling for invalid credentials.

        Verifies that:
        - Invalid usernames are rejected
        - Invalid passwords are rejected
        - Invalid emails are rejected
        - Appropriate exceptions are raised
        """
        with self.assertRaises(InvalidCredentials):
            create_admin_user("ad", "admin@test.com", "Adminpass1!")

        with self.assertRaises(InvalidCredentials):
            create_admin_user("admin", "admin@test.com", "weak")

        with self.assertRaises(InvalidCredentials):
            create_admin_user("admin", "invalid_email", "Adminpass1!")
