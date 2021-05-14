import json

from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.shared.utils import db
from cornflow.tests.const import USER_URL, LOGIN_URL


class TestLogIn(TestCase):
    def create_app(self):
        app = create_app("testing")

        return app

    def setUp(self):
        db.create_all()
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
        self.assertEqual(self.id, response.json["id"])

    def test_validation_error(self):
        payload = self.data
        payload["email"] = "test"

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))
        # self.assertEqual('Not a valid email address.', response.json['error']['email'][0])

    def test_missing_email(self):
        payload = self.data
        payload.pop("email", None)
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))

    def test_missing_password(self):
        payload = self.data
        payload.pop("password", None)
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))

    def test_invalid_email(self):
        payload = self.data
        payload["email"] = "test@test.org"

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))
        self.assertEqual("Invalid credentials", response.json["error"])

    def test_invalid_password(self):
        payload = self.data
        payload["password"] = "testpassword_2"

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))
        self.assertEqual("Invalid credentials", response.json["error"])

    def test_token(self):
        # TODO: implement to check correct token creation
        pass

    def test_old_token(self):
        token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1MzYwNjUsImlhdCI6MTYxMDQ0OTY2NSwic3ViIjoxfQ"
            ".QEfmO-hh55PjtecnJ1RJT3aW2brGLadkg5ClH9yrRnc "
        )

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
