"""
Unit test for the log in endpoint
"""

import json
import logging as log
from unittest import mock

from flask import current_app


from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.shared.const import SERVICE_ROLE, OID_GOOGLE, OID_AZURE, OID_NONE
from cornflow.tests.const import LOGIN_URL
from cornflow.tests.custom_test_case import CustomTestCase, LoginTestCases


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
        """
        Test the successful log in
        """
        super().test_successful_log_in()
        self.assertEqual(self.idx, self.response.json["id"])

    @mock.patch("cornflow.endpoints.login.Auth.generate_token")
    def test_exception_on_token_generation(self, mock_generate_token):
        # Simulate an exception when generate_token is called
        mock_generate_token.side_effect = Exception("Custom exception")

        # Prepare login payload
        payload = self.data

        # Make a login request
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        # Assert that the response is a 400 error
        self.assertEqual(400, response.status_code)
        # Assert that the error message contains the expected text
        self.assertIn("Error in generating user token", response.json["error"])


class TestLogInOpenAuthNoConfig(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        test_user = UserModel(data=self.user_data)
        test_user.save()

        self.user_data.pop("email")

        self.test_user_id = test_user.id

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.service_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Invalid request")

    def test_other_user_password(self):
        """
        Tests that a user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.user_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Invalid request")


class TestLogInOpenAuthAzure(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        app.config["OID_PROVIDER"] = OID_AZURE
        app.config["OID_CLIENT_ID"] = "SOME_SECRET"
        app.config["OID_TENANT_ID"] = "SOME_SECRET"
        app.config["OID_ISSUER"] = "SOME_SECRET"
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login_first_fail(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Token is not valid")

    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_service_user_login_second_fail(self, mock_header):
        """
        Tests second exit point on token validation
        """
        mock_header.get_unverified_header.return_value = None
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Token is missing the headers")

    @mock.patch("cornflow.shared.authentication.auth.jwt")
    def test_service_user_login_third_fail(self, mock_header):
        """
        Tests third exit point on token validation
        """
        mock_header.get_unverified_header.return_value = {"kid": "some_value"}
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertIn(
            "Error getting issuer discovery meta from", response.json["error"]
        )

    @mock.patch("cornflow.endpoints.login.Auth.validate_oid_token")
    def test_service_user_login_no_fail(self, mock_auth):
        mock_auth.return_value = {"preferred_username": "service_user"}
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id, response.json["id"])

    @mock.patch("cornflow.endpoints.login.Auth.validate_oid_token")
    def test_new_user_login_no_fail(self, mock_auth):
        mock_auth.return_value = {"preferred_username": "test_user"}
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id + 1, response.json["id"])


class TestLogInOpenAuthGoogle(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        app.config["OID_PROVIDER"] = OID_GOOGLE
        app.config["OID_CLIENT_ID"] = "SOME_SECRET"
        app.config["OID_TENANT_ID"] = "SOME_SECRET"
        app.config["OID_ISSUER"] = "SOME_SECRET"
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(501, response.status_code)
        self.assertEqual(
            response.json["error"], "The selected OID provider is not implemented"
        )


class TestLogInOpenAuthNone(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        app.config["OID_PROVIDER"] = OID_NONE
        app.config["OID_CLIENT_ID"] = "SOME_SECRET"
        app.config["OID_TENANT_ID"] = "SOME_SECRET"
        app.config["OID_ISSUER"] = "SOME_SECRET"
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(501, response.status_code)
        self.assertEqual(
            response.json["error"], "The OID provider configuration is not valid"
        )


class TestLogInOpenAuthOther(CustomTestCase):
    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] = 0
        app.config["OID_PROVIDER"] = 3
        app.config["OID_CLIENT_ID"] = "SOME_SECRET"
        app.config["OID_TENANT_ID"] = "SOME_SECRET"
        app.config["OID_ISSUER"] = "SOME_SECRET"
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "some_token"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(501, response.status_code)
        self.assertEqual(
            response.json["error"], "The OID provider configuration is not valid"
        )


class TestLogInOpenAuthService(CustomTestCase):

    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing-oauth")
        return app

    def setUp(self):
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.user_data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        test_user = UserModel(data=self.user_data)
        test_user.save()

        self.user_data.pop("email")

        self.test_user_id = test_user.id

        self.service_data = {
            "username": "service_user",
            "email": "service@test.com",
            "password": "Testpassword1!",
        }

        service_user = UserModel(data=self.service_data)
        service_user.save()

        self.service_data.pop("email")
        self.service_user_id = service_user.id

        self.assign_role(self.service_user_id, SERVICE_ROLE)

    def test_service_user_login(self):
        """
        Tests that a service user can log in with username and password
        """

        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.service_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(self.service_user_id, response.json["id"])

    def test_validation_error(self):
        """
        Tests that a user can not log in without token or username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)

    def test_other_user_password(self):
        """
        Tests that a user can not log in with username and password
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.user_data),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json["error"], "Invalid request")

    def test_token_login(self):
        """
        Tests that a user can log in with a token
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"token": "test"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(501, response.status_code)
        self.assertEqual(
            response.json["error"], "The OID provider configuration is not valid"
        )

    def test_log_in_with_all_fields(self):
        """
        Tests that a user can not log in with username and password and a token
        """
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({**self.service_data, "token": "test"}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
