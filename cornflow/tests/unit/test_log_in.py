import json
from flask import current_app

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.const import AUTH_DB, AUTH_LDAP
from cornflow.shared.utils import db
from cornflow.tests.custom_test_case import LoginTestCases
from cornflow.tests.const import USER_URL, LOGIN_URL


class TestLogIn(LoginTestCases.LoginEndpoint):
    def setUp(self):
        super().setUp()
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]

        self.data = {
            "name": "testname",
            "email": "test@test.com",
            "password": "testpassword",
        }
        user = UserModel(data=self.data)
        user.save()
        db.session.commit()
        # we take out the name, we do not need it to sign in
        self.data.pop("name")
        self.id = UserModel.query.filter_by(name="testname").first().id

    def test_successful_log_in(self):
        super().test_successful_log_in()
        self.assertEqual(self.id, self.response.json["id"])
