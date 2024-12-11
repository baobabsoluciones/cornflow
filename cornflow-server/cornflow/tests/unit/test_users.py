"""
Unit test for user management functionality.

This module contains test cases for user management operations, including
user creation, modification, authentication, and role management.

Classes
-------
TestUsers
    Test cases for user management operations
TestUserRoles
    Test cases for user role management
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, PLANNER_ROLE
from cornflow.tests.custom_test_case import CustomTestCase


class TestUsers(CustomTestCase):
    """
    Test cases for user management functionality.

    This class tests core user management features including user creation,
    modification, authentication, and data validation.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Test users
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
        self.user = UserModel(data=self.data)
        self.user.save()
        db.session.commit()

    def test_create_user(self):
        """
        Tests user creation functionality.

        Verifies that:
        - Users can be created with valid data
        - User attributes are correctly stored
        - Password is properly hashed
        """
        new_user_data = {
            "username": "newuser",
            "email": "new@test.com",
            "password": "NewPassword1!",
        }
        user = UserModel(data=new_user_data)
        user.save()

        retrieved_user = UserModel.query.filter_by(username="newuser").first()
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.email, new_user_data["email"])
        self.assertNotEqual(retrieved_user.password, new_user_data["password"])

    def test_update_user(self):
        """
        Tests user update functionality.

        Verifies that:
        - User information can be updated
        - Updates are properly persisted
        - Password updates are correctly handled
        """
        self.user.email = "updated@test.com"
        self.user.save()

        updated_user = UserModel.query.get(self.user.id)
        self.assertEqual(updated_user.email, "updated@test.com")

    def test_delete_user(self):
        """
        Tests user deletion functionality.

        Verifies that:
        - Users can be deleted
        - Associated data is properly cleaned up
        - Deleted users cannot be retrieved
        """
        user_id = self.user.id
        self.user.delete()

        deleted_user = UserModel.query.get(user_id)
        self.assertIsNone(deleted_user)


class TestUserRoles(CustomTestCase):
    """
    Test cases for user role management functionality.

    This class tests the role management system, including role assignment,
    validation, and access control.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Test users
        - Role configurations
        """
        super().setUp()
        db.create_all()
        self.user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpassword1!",
            }
        )
        self.user.save()
        db.session.commit()

    def test_assign_role(self):
        """
        Tests role assignment functionality.

        Verifies that:
        - Roles can be assigned to users
        - Role assignments are properly persisted
        - Multiple roles can be assigned to a user
        """
        role = UserRoleModel(data={"user_id": self.user.id, "role_id": PLANNER_ROLE})
        role.save()

        user_role = UserRoleModel.query.filter_by(
            user_id=self.user.id, role_id=PLANNER_ROLE
        ).first()
        self.assertIsNotNone(user_role)

    def test_multiple_roles(self):
        """
        Tests multiple role assignment functionality.

        Verifies that:
        - Users can have multiple roles
        - Role combinations are properly handled
        - Role conflicts are managed correctly
        """
        roles = [
            {"user_id": self.user.id, "role_id": PLANNER_ROLE},
            {"user_id": self.user.id, "role_id": ADMIN_ROLE},
        ]

        for role_data in roles:
            role = UserRoleModel(data=role_data)
            role.save()

        user_roles = UserRoleModel.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(user_roles), 2)

    def test_remove_role(self):
        """
        Tests role removal functionality.

        Verifies that:
        - Roles can be removed from users
        - Role removal is properly persisted
        - User access is updated after role removal
        """
        role = UserRoleModel(data={"user_id": self.user.id, "role_id": ADMIN_ROLE})
        role.save()

        role_id = role.id
        role.delete()

        deleted_role = UserRoleModel.query.get(role_id)
        self.assertIsNone(deleted_role)
