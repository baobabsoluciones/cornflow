"""
Tests for the conditional endpoints (login and signup) registration.

These endpoints are added to the registered resources only when the
configuration enables them. As the core is mounted in a Blueprint, the Flask
endpoint names carry a prefix (``cornflow.login``) or a suffix (``login_compat``)
that must not leak into the resources, the stored views or the permissions.
"""

import json
from unittest.mock import patch

from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.config import Testing
from cornflow.endpoints import get_resources
from cornflow.endpoints.login import LoginEndpoint
from cornflow.endpoints.signup import SignUpEndpoint
from cornflow.models import UserModel, UserRoleModel, ViewModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    ADMIN_ROLE,
    CONDITIONAL_ENDPOINTS,
    LEGACY_ENDPOINT_SUFFIX,
    NO_SIGNUP,
    PLANNER_ROLE,
    SIGNUP_WITH_AUTH,
    SIGNUP_WITH_NO_AUTH,
)

CANONICAL_PREFIX = "/cornflow"
CANONICAL_SIGNUP_URL = CANONICAL_PREFIX + CONDITIONAL_ENDPOINTS["signup"]
CANONICAL_LOGIN_URL = CANONICAL_PREFIX + CONDITIONAL_ENDPOINTS["login"]
LEGACY_SIGNUP_URL = CONDITIONAL_ENDPOINTS["signup"]
LEGACY_LOGIN_URL = CONDITIONAL_ENDPOINTS["login"]


class BaseConditionalEndpointsTest(TestCase):
    """
    Base class: app created with a given EXTERNAL_APP and SIGNUP_ACTIVATED.
    Subclasses set both values.
    """

    EXTERNAL_APP = 0
    SIGNUP_ACTIVATED = SIGNUP_WITH_NO_AUTH

    def create_app(self):
        with patch.object(Testing, "EXTERNAL_APP", self.EXTERNAL_APP), patch.object(
            Testing, "SIGNUP_ACTIVATED", self.SIGNUP_ACTIVATED
        ):
            return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user_with_role(self, username, role_id):
        user = UserModel(
            {
                "username": username,
                "email": f"{username}@test.com",
                "password": "Testpassword1!",
            }
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role_id}).save()
        return Auth().generate_token(user.id)

    def post_signup(self, url, token, username):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return self.client.post(
            url,
            data=json.dumps(
                {
                    "username": username,
                    "email": f"{username}@new.com",
                    "password": "Testpassword1!",
                }
            ),
            follow_redirects=True,
            headers=headers,
        )


class ConditionalResourcesMixin:
    """Checks on get_resources() when signup is enabled."""

    def test_get_resources_includes_login_and_signup_once(self):
        resources = get_resources()
        by_endpoint = {}
        for res in resources:
            by_endpoint.setdefault(res["endpoint"], []).append(res)

        for name, resource_class in (
            ("login", LoginEndpoint),
            ("signup", SignUpEndpoint),
        ):
            self.assertIn(name, by_endpoint)
            self.assertEqual(1, len(by_endpoint[name]))
            self.assertEqual(
                CONDITIONAL_ENDPOINTS[name], by_endpoint[name][0]["urls"]
            )
            self.assertIs(resource_class, by_endpoint[name][0]["resource"])

    def test_get_resources_has_no_blueprint_or_alias_names(self):
        for res in get_resources():
            self.assertFalse(res["endpoint"].startswith("cornflow."), res["endpoint"])
            self.assertFalse(res["endpoint"].endswith(LEGACY_ENDPOINT_SUFFIX), res["endpoint"])

    def test_get_resources_has_unique_endpoints(self):
        names = [res["endpoint"] for res in get_resources()]
        self.assertEqual(len(names), len(set(names)))

    def test_api_view_has_login_and_signup_with_canonical_url(self):
        login = ViewModel.query.filter_by(name="login").all()
        signup = ViewModel.query.filter_by(name="signup").all()
        self.assertEqual(1, len(login))
        self.assertEqual(1, len(signup))
        self.assertEqual(CANONICAL_LOGIN_URL, login[0].url_rule)
        self.assertEqual(CANONICAL_SIGNUP_URL, signup[0].url_rule)


class TestConditionalEndpointsPluginMode(
    ConditionalResourcesMixin, BaseConditionalEndpointsTest
):
    """Plugin mode (EXTERNAL_APP=0), signup without authentication."""

    EXTERNAL_APP = 0
    SIGNUP_ACTIVATED = SIGNUP_WITH_NO_AUTH


class TestConditionalEndpointsLegacyMode(
    ConditionalResourcesMixin, BaseConditionalEndpointsTest
):
    """Legacy mode (EXTERNAL_APP=1), signup without authentication."""

    EXTERNAL_APP = 1
    SIGNUP_ACTIVATED = SIGNUP_WITH_NO_AUTH


class TestConditionalEndpointsSignupDeactivated(BaseConditionalEndpointsTest):
    """Signup disabled: login stays registered, signup does not."""

    SIGNUP_ACTIVATED = NO_SIGNUP

    def test_get_resources_has_login_but_not_signup(self):
        names = [res["endpoint"] for res in get_resources()]
        self.assertEqual(1, names.count("login"))
        self.assertNotIn("signup", names)

    def test_api_view_has_login_but_not_signup(self):
        self.assertIsNotNone(ViewModel.query.filter_by(name="login").first())
        self.assertIsNone(ViewModel.query.filter_by(name="signup").first())


class SignupWithAuthMixin:
    """Signup with authentication (SIGNUP_ACTIVATED=2) through both routes."""

    SIGNUP_ACTIVATED = SIGNUP_WITH_AUTH

    def test_admin_can_signup_through_canonical_route(self):
        token = self.create_user_with_role("admin", ADMIN_ROLE)
        response = self.post_signup(CANONICAL_SIGNUP_URL, token, "newuser")
        self.assertEqual(201, response.status_code)
        self.assertIsNotNone(UserModel.get_one_user_by_email("newuser@new.com"))

    def test_admin_can_signup_through_legacy_route(self):
        token = self.create_user_with_role("admin", ADMIN_ROLE)
        response = self.post_signup(LEGACY_SIGNUP_URL, token, "newuser")
        self.assertEqual(201, response.status_code)
        self.assertIsNotNone(UserModel.get_one_user_by_email("newuser@new.com"))

    def test_non_admin_is_denied_for_lack_of_permission(self):
        token = self.create_user_with_role("planner", PLANNER_ROLE)
        for url in (CANONICAL_SIGNUP_URL, LEGACY_SIGNUP_URL):
            response = self.post_signup(url, token, "newuser")
            self.assertEqual(403, response.status_code)
            self.assertNotIn("not in the database", response.json["error"])
        self.assertIsNone(UserModel.get_one_user_by_email("newuser@new.com"))


class TestSignupWithAuthPluginMode(SignupWithAuthMixin, BaseConditionalEndpointsTest):
    EXTERNAL_APP = 0


class TestSignupWithAuthLegacyMode(SignupWithAuthMixin, BaseConditionalEndpointsTest):
    EXTERNAL_APP = 1
