"""
Unit test for the log in endpoint
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import LoginTestCases


class TestLogIn(LoginTestCases.LoginEndpoint):
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
        # we take out the email, we do not need it to log in
        self.data.pop("email")
        self.idx = UserModel.query.filter_by(username="testname").first().id

    def test_successful_log_in(self):
        super().test_successful_log_in()
        self.assertEqual(self.idx, self.response.json["id"])
