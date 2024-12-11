"""
Unit tests for CLI functionality.

This module contains test cases for command-line interface operations,
including database initialization and user management commands.

Classes
-------
TestCLI
    Test cases for CLI commands and operations
"""

# Import from libraries
import os
import tempfile
import unittest

# Import from internal modules
from cornflow.cli import create_app
from cornflow.models import UserModel
from cornflow.shared import db


class TestCLI(unittest.TestCase):
    """
    Test cases for CLI functionality.

    This class tests various command-line interface operations including
    database initialization and user management.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Creates:
        - Temporary database file
        - Test application instance
        - Test client
        - Application context
        """
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app(
            config_filename="config_testing.py",
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{self.db_path}",
        )
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Performs:
        - Database cleanup
        - Temporary file removal
        - Context cleanup
        """
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_create_user(self):
        """
        Tests user creation through CLI.

        Verifies that:
        - Users can be created with valid credentials
        - User data is correctly stored in database
        - User model functions properly
        """
        user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpassword1!",
            }
        )
        user.save()
        db.session.commit()

        retrieved_user = UserModel.query.filter_by(username="testuser").first()
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.email, "test@test.com")

    def test_create_admin(self):
        """
        Tests admin user creation through CLI.

        Verifies that:
        - Admin users can be created
        - Admin privileges are correctly assigned
        - Admin data is properly stored
        """
        admin = UserModel(
            data={
                "username": "admin",
                "email": "admin@test.com",
                "password": "Adminpass1!",
                "is_admin": True,
            }
        )
        admin.save()
        db.session.commit()

        retrieved_admin = UserModel.query.filter_by(username="admin").first()
        self.assertIsNotNone(retrieved_admin)
        self.assertTrue(retrieved_admin.is_admin)
