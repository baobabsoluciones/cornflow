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

    def tearDown(self):
        super().tearDown()

    def test_successful_log_in(self):
        super().test_successful_log_in()
        self.assertEqual(self.id, self.response.json["id"])

    def test_token(self):
        # TODO: implement to check correct token creation
        pass

    def test_old_token(self):
        token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1MzYwNjUsImlhdCI6MTYxMDQ0OTY2NSwic3ViIjoxfQ"
            ".QEfmO-hh55PjtecnJ1RJT3aW2brGLadkg5ClH9yrRnc "
        )

        if self.AUTH_TYPE == AUTH_LDAP:
            payload = self.data

            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            self.id = response.json["id"]

        response = self.client.get(
            USER_URL + str(self.id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("Token expired, please login again", response.json["error"])

    def test_bad_format_token(self):
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        token = response.json["token"]

        if self.AUTH_TYPE == AUTH_LDAP:
            self.id = response.json["id"]

        response = self.client.get(
            USER_URL + str(self.id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer" + token,
            },
        )
        self.assertEqual(400, response.status_code)

    def test_invalid_token(self):
        token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1Mzk5NTMsImlhdCI6MTYxMDQ1MzU1Mywic3ViIjoxfQ"
            ".g3Gh7k7twXZ4K2MnQpgpSr76Sl9VX6TkDWusX5YzImo"
        )

        if self.AUTH_TYPE == AUTH_LDAP:
            payload = self.data

            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )
            self.id = response.json["id"]

        response = self.client.get(
            USER_URL + str(self.id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "Invalid token, please try again with a new token", response.json["error"]
        )
