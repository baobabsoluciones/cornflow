"""
Integration tests for the login with ldap
"""

# Import from libraries
from flask import current_app
import json

# Import from internal modules
from cornflow.commands import RegisterRoles, AccessInitialization
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import PLANNER_ROLE
from cornflow.tests.const import USER_URL
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
        self.data = {"email": "administrator", "password": "administrator1234"}
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

    def test_restricted_access(self):
        AccessInitialization().run()
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
        AccessInitialization().run()
        super().test_successful_log_in()
        payload = self.data
        payload["name"] = "some_name"
        payload["id"] = self.response.json["id"]
        response = self.client.put(
            USER_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.response.json["token"],
            },
        )
        self.assertEqual(501, response.status_code)
        self.assertEqual("To edit a user, go to LDAP server", response.json["error"])
