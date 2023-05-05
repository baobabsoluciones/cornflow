"""
Unit test for the token endpoint
"""

# Import from libraries
from flask import current_app
import json

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CheckTokenTestCase
from cornflow.tests.const import LOGIN_URL


class TestCheckToken(CheckTokenTestCase.TokenEndpoint):
    def setUp(self):
        super().setUp()
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }
        user = UserModel(data=self.data)
        user.save()
        db.session.commit()
        self.data.pop("email")

    def test_get_valid_token(self):
        payload = self.data
        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        self.get_check_token()
        self.assertEqual(200, self.response.status_code)
        self.assertEqual(1, self.response.json["valid"])

    def test_get_invalid_token(self):
        self.token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2Mzk4MjAwNzMsImlhdCI6MTYzOTczMzY3Mywic3ViIjoxfQ"
        self.token += ".KzAYFDSrAJoCrnxGqKL2v6fE3oxT2muBgYztF1wcuN8"

        self.get_check_token()

        self.assertEqual(200, self.response.status_code)
        self.assertEqual(0, self.response.json["valid"])

    def test_no_token(self):
        self.get_check_token()

        self.assertEqual(400, self.response.status_code)

    def test_old_token(self):
        self.token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1MzYwNjUsImlhdCI6MTYxMDQ0OTY2NSwic3ViIjoxfQ"
            ".QEfmO-hh55PjtecnJ1RJT3aW2brGLadkg5ClH9yrRnc "
        )

        self.get_check_token()
        self.assertEqual(200, self.response.status_code)
        self.assertEqual(0, self.response.json["valid"])
