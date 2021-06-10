"""
Integration tests for the login with ldap
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.commands import RegisterRoles
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import PLANNER_ROLE
from cornflow.tests.custom_test_case import LoginTestCases


class TestLogIn(LoginTestCases.LoginEndpoint):
    def setUp(self):
        super().setUp()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {"email": "planner", "password": "planner1234"}

    def tearDown(self):
        super().tearDown()

    def test_successful_log_in(self):
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["email"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_viewer(self):
        self.data = {"email": "viewer", "password": "viewer1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["email"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_admin(self):
        self.data = {"email": "admin", "password": "admin1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["email"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_service(self):
        self.data = {"email": "cornflow", "password": "cornflow1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["email"]).id,
            self.response.json["id"],
        )

    def test_role_registration(self):
        RegisterRoles().run()
        super().test_successful_log_in()
        user_role = UserRoleModel.query.filter_by(
            user_id=self.response.json["id"], role_id=PLANNER_ROLE
        )
        self.assertNotEqual(None, user_role)
