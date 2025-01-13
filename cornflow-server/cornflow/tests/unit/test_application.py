"""
File to test different application configurations
"""

import json
import logging as log

from flask import current_app

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.shared import db
from cornflow.tests.const import LOGIN_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestApplicationRoot(CustomTestCase):

    def create_app(self):
        return create_app("testing-root")

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        user = UserModel(self.data)
        user.save()

        self.data.pop("email")

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_wrong_route(self):
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 404)

    def test_correct_route(self):
        response = self.client.post(
            f"{current_app.config['APPLICATION_ROOT']}{LOGIN_URL}",
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
