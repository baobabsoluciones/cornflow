"""
Integration tests for the login with ldap
"""

# Import from libraries
from flask import current_app
import json

# Import from internal modules
from cornflow.app import create_app, register_roles, access_init
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import PLANNER_ROLE
from cornflow.tests.const import SIGNUP_URL, USER_ROLE_URL, USER_URL
from cornflow.tests.custom_test_case import LoginTestCases


class TestLogIn(LoginTestCases.LoginEndpoint):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        super().setUp()
        self.runner = create_app().test_cli_runner()
        self.runner.invoke(register_roles, ["-v"])
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {"username": "planner", "password": "planner1234"}

    def test_successful_log_in(self):
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["username"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_viewer(self):
        self.data = {"username": "viewer", "password": "viewer1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["username"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_admin(self):
        self.data = {"username": "administrator", "password": "administrator1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["username"]).id,
            self.response.json["id"],
        )

    def test_successful_log_in_service(self):
        self.data = {"username": "cornflow", "password": "cornflow1234"}
        super().test_successful_log_in()
        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["username"]).id,
            self.response.json["id"],
        )

    def test_user_table_registration(self):
        user_table_before = UserModel.query.all()
        super().test_successful_log_in()
        user_table_after = UserModel.query.all()
        self.assertNotEqual(user_table_before, user_table_after)
        self.assertNotEqual(len(user_table_before), len(user_table_after))

    def test_role_registration(self):
        user_role_before = UserRoleModel.query.all()

        super().test_successful_log_in()
        user_role_after = UserRoleModel.query.all()

        self.assertNotEqual(None, user_role_after)
        self.assertNotEqual(user_role_before, user_role_after)
        self.assertNotEqual(len(user_role_before), len(user_role_after))

    def test_restricted_access(self):
        self.runner.invoke(access_init)
        super().test_successful_log_in()
        response = self.client.get(
            USER_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.response.json["token"],
            },
        )
        self.assertEqual(403, response.status_code)

    def test_deactivated_endpoint(self):
        self.runner.invoke(access_init)
        self.data = {"username": "administrator", "password": "administrator1234"}
        super().test_successful_log_in()
        payload = {"user_id": self.response.json["id"], "role_id": PLANNER_ROLE}
        response = self.client.post(
            USER_ROLE_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.response.json["token"],
            },
        )
        self.assertEqual(501, response.status_code)

    def test_deactivated_sign_up(self):
        self.runner.invoke(register_roles)
        payload = {
            "username": "testuser",
            "email": "testemail@example.org",
            "password": "Testpassword1!",
        }
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(404, response.status_code)
