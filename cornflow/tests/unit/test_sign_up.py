import json

from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands import AccessInitialization
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import PLANNER_ROLE
from cornflow.shared.utils import db
from cornflow.tests.const import SIGNUP_URL


class TestSignUp(TestCase):
    def create_app(self):
        app = create_app("testing")

        return app

    def setUp(self):
        db.create_all()
        AccessInitialization().run()
        self.data = {
            "name": "testname",
            "email": "test@test.com",
            "password": "testpassword",
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_successful_signup(self):
        payload = self.data

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(str, type(response.json["token"]))
        self.assertEqual(int, type(response.json["id"]))
        self.assertEqual(
            PLANNER_ROLE,
            UserRoleModel.query.filter_by(user_id=response.json["id"]).first().role_id,
        )
        self.assertNotEqual(None, UserModel.get_one_user_by_email(self.data["email"]))

    # Test that registering again with the same name give an error
    def test_existing_name_signup(self):
        payload = self.data

        self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        response2 = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response2.status_code)
        self.assertTrue("error" in response2.json)
        self.assertEqual(str, type(response2.json["error"]))

    def test_validation_error(self):
        payload = self.data
        payload["email"] = "test"

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))
