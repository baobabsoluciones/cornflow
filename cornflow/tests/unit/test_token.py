"""
Unit test for the token endpoint
"""

# Import from libraries
from flask import current_app
import json

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared.utils import db
from cornflow.tests.custom_test_case import CheckTokenTestCase
from cornflow.tests.const import LOGIN_URL, TOKEN_URL


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
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        self.test_get_token(token)

    def test_get_invalid_token(self):
        token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2Mzk4MjAwNzMsImlhdCI6MTYzOTczMzY3Mywic3ViIjoxfQ'
        token += '.KzAYFDSrAJoCrnxGqKL2v6fE3oxT2muBgYztF1wcuN8'

        self.test_get_token(token, expected_status=200, check_valid=0)

    def test_no_token(self):
        response = self.client.get(
            TOKEN_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
            },
        )

        self.assertEqual(400, response.status_code)
