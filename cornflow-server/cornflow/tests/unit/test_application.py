"""
File to test different application configurations
"""

import json
import logging as log

from unittest.mock import patch

from flask import current_app

from cornflow.app import create_app
from cornflow.models import UserModel
from cornflow.commands.access import access_init_command
from cornflow.config import TestingApplicationRoot
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.shared import db
from cornflow.tests.const import LOGIN_URL
from cornflow.tests.custom_test_case import CustomTestCase


class BaseApplicationRootTest(CustomTestCase):
    """
    Base class: app created with the testing-root configuration
    (APPLICATION_ROOT="/test") and the EXTERNAL_APP value set by each subclass.
    """

    EXTERNAL_APP = 0

    def create_app(self):
        with patch.object(TestingApplicationRoot, "EXTERNAL_APP", self.EXTERNAL_APP):
            return create_app("testing-root")

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Kx9#tR2m!Qw7Zp",
        }

        user = UserModel(self.data)
        user.save()

        self.data.pop("email")

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, url):
        return self.client.post(
            url,
            data=json.dumps(self.data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )


class TestApplicationRoot(BaseApplicationRootTest):
    """
    Legacy mode (EXTERNAL_APP=1): the whole app is mounted under
    APPLICATION_ROOT through DispatcherMiddleware.
    """

    EXTERNAL_APP = 1

    def test_wrong_route(self):
        # Outside APPLICATION_ROOT nothing is served
        self.assertEqual(self.login(LOGIN_URL).status_code, 404)
        self.assertEqual(self.login(f"/cornflow{LOGIN_URL}").status_code, 404)

    def test_correct_route(self):
        # Legacy (unprefixed) route under APPLICATION_ROOT
        response = self.login(f"{current_app.config['APPLICATION_ROOT']}{LOGIN_URL}")
        self.assertEqual(response.status_code, 200)

    def test_correct_canonical_route_under_root(self):
        # Canonical /cornflow route under APPLICATION_ROOT
        response = self.login(
            f"{current_app.config['APPLICATION_ROOT']}/cornflow{LOGIN_URL}"
        )
        self.assertEqual(response.status_code, 200)


class TestApplicationRootPluginMode(BaseApplicationRootTest):
    """
    Plugin mode (EXTERNAL_APP=0): no DispatcherMiddleware, APPLICATION_ROOT
    is not mounted; core routes live under /cornflow with unprefixed aliases.
    """

    EXTERNAL_APP = 0

    def test_canonical_route(self):
        self.assertEqual(self.login(f"/cornflow{LOGIN_URL}").status_code, 200)

    def test_legacy_alias_route(self):
        self.assertEqual(self.login(LOGIN_URL).status_code, 200)

    def test_application_root_not_mounted(self):
        root = current_app.config["APPLICATION_ROOT"]
        self.assertEqual(self.login(f"{root}{LOGIN_URL}").status_code, 404)
        self.assertEqual(self.login(f"{root}/cornflow{LOGIN_URL}").status_code, 404)
