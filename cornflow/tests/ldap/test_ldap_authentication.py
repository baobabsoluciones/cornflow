import json
from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.const import AUTH_DB, AUTH_LDAP
from cornflow.shared.utils import db
from cornflow.tests.const import USER_URL, LOGIN_URL


class TestLogIn(TestCase):
    def create_app(self):
        app = create_app("testing")

        return app

    def setUp(self):
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {"email": "planner", "password": "planner1234"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_successful_log_in(self):
        payload = self.data

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(str, type(response.json["token"]))

        self.assertEqual(
            UserModel.get_one_user_by_username(self.data["email"]).id,
            response.json["id"],
        )
