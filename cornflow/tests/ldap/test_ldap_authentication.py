import json
from flask import current_app


from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.const import AUTH_DB, AUTH_LDAP
from cornflow.shared.utils import db
from cornflow.tests.const import USER_URL, LOGIN_URL
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
