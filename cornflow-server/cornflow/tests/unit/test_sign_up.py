"""
Unit test for the sign-up endpoint
"""

# Import from libraries

# Import from internal modules

import json
from unittest.mock import patch

# Import from libraries
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.commands import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.models import UserModel, UserRoleModel, ViewModel, PermissionViewRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    ADMIN_ROLE,
    NO_SIGNUP,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    POST_ACTION,
    SIGNUP_PLATFORM_ADMIN_ONLY,
    SIGNUP_WITH_AUTH,
)
from cornflow.tests.const import SIGNUP_URL


class TestSignUp(TestCase):
    def create_app(self):
        app = create_app("testing")

        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Kx9#tR2m!Qw7Zp",
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_self_signup_password_is_not_single_use(self):
        # The owner chose the password themselves: no forced change
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(201, response.status_code)
        user = UserModel.get_one_user(response.json["id"])
        self.assertFalse(user.pwd_change_required)

    def test_successful_signup(self):
        payload = self.data

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(str, type(response.json["token"]))
        self.assertEqual(int, type(response.json["id"]))
        self.assertEqual(
            PLANNER_ROLE,
            UserRoleModel.query.filter_by(user_id=response.json["id"]).first().role_id,
        )
        self.assertNotEqual(None, UserModel.get_one_user_by_email(self.data["email"]))

    # Test that registering again with the same name give an error
    def test_existing_name_signup(self):
        payload = self.data

        self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        response2 = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response2.status_code)
        self.assertTrue("error" in response2.json)
        self.assertEqual(str, type(response2.json["error"]))

    def test_validation_error(self):
        payload = self.data
        payload["email"] = "test"

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))


class TestSignUpDeactivated(TestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["SIGNUP_ACTIVATED"] = NO_SIGNUP
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_signup_deactivated(self):
        payload = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Kx9#tR2m!Qw7Zp",
        }

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)


class TestSignUpAuthenticated(TestCase):
    """Test the authenticated signup endpoint (SIGNUP_ACTIVATED=SIGNUP_WITH_AUTH)"""

    def create_app(self):
        with patch("cornflow.config.Testing.SIGNUP_ACTIVATED", SIGNUP_WITH_AUTH):
            app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        # Create test data
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Kx9#tR2m!Qw7Zp",
        }

        # Create an admin user for testing
        self.admin_user = UserModel(
            {
                "username": "admin",
                "email": "admin@test.com",
                "password": "Am9!cV4b#Ls6Qe",
            }
        )
        self.admin_user.save()

        # Assign admin role to the user
        admin_role = UserRoleModel(
            {"user_id": self.admin_user.id, "role_id": ADMIN_ROLE}
        )
        admin_role.save()

        # Create a regular user for testing
        self.regular_user = UserModel(
            {
                "username": "regular",
                "email": "regular@test.com",
                "password": "Rg3$hJ7u!Pw9Bn",
            }
        )
        self.regular_user.save()

        # Assign planner role to the user
        planner_role = UserRoleModel(
            {"user_id": self.regular_user.id, "role_id": PLANNER_ROLE}
        )
        planner_role.save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def get_auth_token(self, user):
        """Helper method to get authentication token for a user"""
        auth = Auth()
        return auth.generate_token(user.id)

    def test_admin_provisioned_password_is_single_use(self):
        # An administrator knows the password they typed: the account must
        # change it on first login (same reasoning as an admin reset)
        admin_token = self.get_auth_token(self.admin_user)
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}",
            },
        )
        self.assertEqual(201, response.status_code)
        user = UserModel.get_one_user(response.json["id"])
        self.assertTrue(user.pwd_change_required)

    def test_authenticated_signup_admin_can_register(self):
        """Test that admin users can register new users"""
        payload = self.data
        admin_token = self.get_auth_token(self.admin_user)

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}",
            },
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(str, type(response.json["token"]))
        self.assertEqual(int, type(response.json["id"]))
        self.assertEqual(
            PLANNER_ROLE,
            UserRoleModel.query.filter_by(user_id=response.json["id"]).first().role_id,
        )
        self.assertNotEqual(None, UserModel.get_one_user_by_email(self.data["email"]))

    def test_authenticated_signup_regular_user_cannot_register(self):
        """Test that regular users cannot register new users"""
        payload = self.data
        regular_token = self.get_auth_token(self.regular_user)

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {regular_token}",
            },
        )

        # Should return 403 Forbidden due to insufficient permissions
        self.assertEqual(403, response.status_code)
        self.assertIn("error", response.json)

    def test_authenticated_signup_no_auth_header_fails(self):
        """Test that signup fails without authentication header"""
        payload = self.data

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        # Should return 400 Bad Request due to missing authorization
        self.assertEqual(400, response.status_code)
        self.assertIn("error", response.json)

    def test_authenticated_signup_invalid_token_fails(self):
        """Test that signup fails with invalid token"""
        payload = self.data

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token",
            },
        )

        # Should return 400 Bad Request due to invalid token
        self.assertEqual(400, response.status_code)
        self.assertIn("error", response.json)

    def test_signup_permissions_are_registered_in_database(self):
        """Test that signup permissions are properly registered in the database"""
        # Check that the signup endpoint exists in the views table
        signup_view = ViewModel.query.filter_by(name="signup").first()
        self.assertIsNotNone(
            signup_view, "Signup endpoint should be registered in views table"
        )
        self.assertEqual("/signup/", signup_view.url_rule)

        # Check that admin role has permissions for signup endpoint
        admin_permissions = PermissionViewRoleModel.query.filter_by(
            role_id=ADMIN_ROLE, api_view_id=signup_view.id
        ).all()

        # Admin should have POST permission for signup endpoint
        self.assertGreater(
            len(admin_permissions),
            0,
            "Admin should have permissions for signup endpoint",
        )

        # Verify that the permission is for POST action
        post_permission = PermissionViewRoleModel.query.filter_by(
            role_id=ADMIN_ROLE, api_view_id=signup_view.id, action_id=POST_ACTION
        ).first()

        self.assertIsNotNone(
            post_permission, "Admin should have POST permission for signup endpoint"
        )


class TestSignUpPlatformAdminOnly(TestCase):
    """SIGNUP_ACTIVATED=SIGNUP_PLATFORM_ADMIN_ONLY: only platform admins provision accounts."""

    def create_app(self):
        with patch(
            "cornflow.config.Testing.SIGNUP_ACTIVATED", SIGNUP_PLATFORM_ADMIN_ONLY
        ):
            app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Kx9#tR2m!Qw7Zp",
        }
        self.platform_admin = UserModel(
            {
                "username": "platadmin",
                "email": "platadmin@test.com",
                "password": "Am9!cV4b#Ls6Qe",
            }
        )
        self.platform_admin.save()
        UserRoleModel(
            {"user_id": self.platform_admin.id, "role_id": PLATFORM_ADMIN_ROLE}
        ).save()
        self.client_admin = UserModel(
            {
                "username": "clientadmin",
                "email": "clientadmin@test.com",
                "password": "Rg3$hJ7u!Pw9Bn",
            }
        )
        self.client_admin.save()
        UserRoleModel(
            {"user_id": self.client_admin.id, "role_id": ADMIN_ROLE}
        ).save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def signup_as(self, user):
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["Authorization"] = f"Bearer {Auth().generate_token(user.id)}"
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers=headers,
        )

    def test_platform_admin_can_provision(self):
        response = self.signup_as(self.platform_admin)
        self.assertEqual(201, response.status_code)
        # the password is known by the admin: single-use
        user = UserModel.get_one_user(response.json["id"])
        self.assertTrue(user.pwd_change_required)

    def test_client_admin_can_not_provision(self):
        response = self.signup_as(self.client_admin)
        self.assertEqual(403, response.status_code)
        self.assertIsNone(UserModel.get_one_user_by_username("testname"))

    def test_unauthenticated_can_not_provision(self):
        response = self.signup_as(None)
        self.assertGreaterEqual(response.status_code, 400)
        self.assertIsNone(UserModel.get_one_user_by_username("testname"))
