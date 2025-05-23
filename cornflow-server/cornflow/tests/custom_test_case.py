"""
This file contains the different custom test classes used to generalize the unit testing of cornflow.
It provides base test cases and utilities for testing authentication, API endpoints, and database operations.

Classes
-------
CustomTestCase
    Base test case class with common testing utilities
BaseTestCases
    Container for common test case scenarios
CheckTokenTestCase
    Test cases for token validation
LoginTestCases
    Test cases for login functionality
"""

import json

# Import from libraries
import logging as log
from datetime import datetime, timedelta, timezone
from typing import List

import jwt
from flask import current_app
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.models import UserRoleModel, UserModel
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    SERVICE_ROLE,
    INTERNAL_TOKEN_ISSUER,
)
from cornflow.shared import db
from cornflow.tests.const import (
    LOGIN_URL,
    SIGNUP_URL,
    USER_URL,
    USER_ROLE_URL,
    TOKEN_URL,
)

try:
    date_from_str = datetime.fromisoformat
except:

    def date_from_str(_string):
        return datetime.strptime(_string, "%Y-%m-%dT%H:%M:%S.%f")


class CustomTestCase(TestCase):
    """
    Base test case class that provides common utilities for testing Cornflow applications.

    This class sets up a test environment with a test database, user authentication,
    and common test methods for CRUD operations.
    """

    def create_app(self):
        """
        Creates and configures a Flask application for testing.

        :returns: A configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing")
        return app

    @staticmethod
    def load_file(_file, fk=None, fk_id=None):
        """
        Loads and optionally modifies a JSON file.

        :param str _file: Path to the JSON file to load
        :param str fk: Foreign key field name to modify (optional)
        :param int fk_id: Foreign key ID value to set (optional)
        :returns: The loaded and potentially modified JSON data
        :rtype: dict
        """
        with open(_file) as f:
            temp = json.load(f)
        if fk is not None and fk_id is not None:
            temp[fk] = fk_id
        return temp

    def setUp(self):
        """
        Sets up the test environment before each test.

        Creates database tables, initializes access controls, and creates a test user.
        """
        log.root.setLevel(current_app.config["LOG_LEVEL"])
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        data = {
            "username": "testname",
            "email": "test@test.com",
            "password": "Testpassword1!",
        }

        self.client.post(
            SIGNUP_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

        data.pop("email")

        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        data = Auth().decode_token(self.token)
        self.user = UserModel.get_one_object(username=data["sub"])
        self.url = None
        self.model = None
        self.copied_items = set()
        self.items_to_check = []
        self.roles_with_access = []

    @staticmethod
    def get_header_with_auth(token):
        """
        Creates HTTP headers with authentication token.

        :param str token: JWT authentication token
        :returns: Headers dictionary with content type and authorization
        :rtype: dict
        """
        return {"Content-Type": "application/json", "Authorization": "Bearer " + token}

    def create_user(self, data):
        """
        Creates a new user through the API.

        :param dict data: Dictionary containing user data (username, email, password)
        :returns: API response from user creation
        :rtype: Response
        """
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

    @staticmethod
    def assign_role(user_id, role_id):
        """
        Assigns a role to a user in the database.

        :param int user_id: ID of the user
        :param int role_id: ID of the role to assign
        :returns: The created or existing user role association
        :rtype: UserRoleModel
        """
        if UserRoleModel.check_if_role_assigned(user_id, role_id):
            user_role = UserRoleModel.query.filter_by(
                user_id=user_id, role_id=role_id
            ).first()
        else:
            user_role = UserRoleModel({"user_id": user_id, "role_id": role_id})
            user_role.save()
        return user_role

    def create_role_endpoint(self, user_id, role_id, token):
        """
        Creates a role assignment through the API endpoint.

        :param int user_id: ID of the user
        :param int role_id: ID of the role to assign
        :param str token: Authentication token
        :returns: API response from role assignment
        :rtype: Response
        """
        return self.client.post(
            USER_ROLE_URL,
            data=json.dumps({"user_id": user_id, "role_id": role_id}),
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

    def create_user_with_role(self, role_id):
        """
        Creates a new user and assigns them a specific role.

        :param int role_id: ID of the role to assign
        :returns: Authentication token for the created user
        :rtype: str
        """
        data = {
            "username": "testuser" + str(role_id),
            "email": "testemail" + str(role_id) + "@test.org",
            "password": "Testpassword1!",
        }
        response = self.create_user(data)
        self.assign_role(response.json["id"], role_id)

        data.pop("email")
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

    def create_service_user(self):
        """
        Creates a new user with service role.

        :returns: Authentication token for the service user
        :rtype: str
        """
        return self.create_user_with_role(SERVICE_ROLE)

    def create_admin(self):
        """
        Creates a new user with admin role.

        :returns: Authentication token for the admin user
        :rtype: str
        """
        return self.create_user_with_role(ADMIN_ROLE)

    def create_planner(self):
        """
        Creates a new user with planner role.

        :returns: Authentication token for the planner user
        :rtype: str
        """
        return self.create_user_with_role(PLANNER_ROLE)

    def tearDown(self):
        """
        Cleans up the test environment after each test.
        """
        db.session.remove()
        db.drop_all()

    def create_new_row(
        self, url, model, payload, expected_status=201, check_payload=True, token=None
    ):
        """
        Creates a new database row through the API.

        :param str url: API endpoint URL
        :param class model: Database model class
        :param dict payload: Data to create the row
        :param int expected_status: Expected HTTP status code (default: 201)
        :param bool check_payload: Whether to verify the created data (default: True)
        :param str token: Authentication token (optional)
        :returns: ID of the created row
        :rtype: int
        """
        token = token or self.token

        response = self.client.post(
            url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

        self.assertEqual(expected_status, response.status_code)
        if not check_payload:
            return response.json
        row = model.query.get(response.json["id"])
        self.assertEqual(row.id, response.json["id"])

        for key in self.get_keys_to_check(payload):
            getattr(row, key)
            if key in payload:
                self.assertEqual(getattr(row, key), payload[key])
        return row.id

    def get_rows(
        self, url, data, token=None, check_data=True, keys_to_check: List[str] = None
    ):
        """
        Retrieves multiple rows through the API and verifies their contents.

        :param str url: API endpoint URL
        :param list data: List of data dictionaries to create and verify
        :param str token: Authentication token (optional)
        :param bool check_data: Whether to verify the retrieved data (default: True)
        :param list keys_to_check: Specific keys to verify in the response (optional)
        :returns: API response containing the rows
        :rtype: Response
        """
        token = token or self.token

        codes = [
            self.create_new_row(url=url, model=self.model, payload=d) for d in data
        ]
        rows = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        # rows now come in desc order of date, so we reverse them:
        rows_data = list(reversed(rows.json))
        self.assertEqual(len(rows.json), len(data))
        if check_data:
            for i in range(len(data)):
                self.assertEqual(rows_data[i]["id"], codes[i])
                if keys_to_check:
                    self.assertCountEqual(list(rows_data[i].keys()), keys_to_check)
                for key in self.get_keys_to_check(data[i]):
                    self.assertIn(key, rows_data[i])
                    if key in data[i]:
                        self.assertEqual(rows_data[i][key], data[i][key])
        return rows

    def get_keys_to_check(self, payload):
        """
        Determines which keys should be checked in API responses.

        :param dict payload: Data dictionary containing keys
        :returns: List of keys to check
        :rtype: list
        """
        if len(self.items_to_check):
            return self.items_to_check
        return payload.keys()

    def get_one_row(
        self,
        url,
        payload,
        expected_status=200,
        check_payload=True,
        token=None,
        keys_to_check: List[str] = None,
    ):
        """
        Retrieves a single row through the API and verifies its contents.

        :param str url: API endpoint URL
        :param dict payload: Expected data dictionary
        :param int expected_status: Expected HTTP status code (default: 200)
        :param bool check_payload: Whether to verify the retrieved data (default: True)
        :param str token: Authentication token (optional)
        :param list keys_to_check: Specific keys to verify in the response (optional)
        :returns: API response data
        :rtype: dict
        """
        token = token or self.token

        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )

        self.assertEqual(expected_status, row.status_code)
        if not check_payload:
            return row.json
        if keys_to_check:
            self.assertCountEqual(list(row.json.keys()), keys_to_check)
        self.assertEqual(row.json["id"], payload["id"])
        for key in self.get_keys_to_check(payload):
            self.assertIn(key, row.json)
            if key in payload:
                self.assertEqual(row.json[key], payload[key])
        return row.json

    def get_no_rows(self, url, token=None):
        """
        Verifies that no rows are returned from the API endpoint.

        :param str url: API endpoint URL
        :param str token: Authentication token (optional)
        :returns: Empty list from API response
        :rtype: list
        """
        token = token or self.token
        rows = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )
        self.assertEqual(200, rows.status_code)
        self.assertEqual(rows.json, [])
        return rows.json

    def update_row(
        self,
        url,
        change,
        payload_to_check,
        expected_status=200,
        check_payload=True,
        token=None,
    ):
        """
        Updates a row through the API and verifies the changes.

        :param str url: API endpoint URL
        :param dict change: Dictionary of changes to apply
        :param dict payload_to_check: Expected data after update
        :param int expected_status: Expected HTTP status code (default: 200)
        :param bool check_payload: Whether to verify the updated data (default: True)
        :param str token: Authentication token (optional)
        :returns: Updated row data
        :rtype: dict
        """
        token = token or self.token

        response = self.client.put(
            url,
            data=json.dumps(change),
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

        self.assertEqual(expected_status, response.status_code)

        if not check_payload:
            return response.json

        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )

        self.assertEqual(200, row.status_code)
        self.assertEqual(row.json["id"], payload_to_check["id"])

        for key in self.get_keys_to_check(payload_to_check):
            self.assertIn(key, row.json)
            if key in payload_to_check:
                self.assertEqual(row.json[key], payload_to_check[key])

        return row.json

    def patch_row(
        self, url, json_patch, payload_to_check, expected_status=200, check_payload=True
    ):
        """
        Patches a row through the API and verifies the changes.

        :param str url: API endpoint URL
        :param dict json_patch: JSON patch operations to apply
        :param dict payload_to_check: Expected data after patch
        :param int expected_status: Expected HTTP status code (default: 200)
        :param bool check_payload: Whether to verify the patched data (default: True)
        """
        response = self.client.patch(
            url,
            data=json.dumps(json_patch),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )

        self.assertEqual(expected_status, response.status_code)

        if not check_payload:
            return response.json

        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )

        self.assertEqual(expected_status, row.status_code)
        self.assertEqual(payload_to_check["data"], row.json["data"])
        self.assertEqual(payload_to_check["solution"], row.json["solution"])

    def delete_row(self, url):
        """
        Deletes a row through the API and verifies its removal.

        :param str url: API endpoint URL
        :returns: API response from the delete operation
        :rtype: Response
        """
        response = self.client.delete(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )
        self.assertEqual(200, response.status_code)

        response = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(self.token)
        )

        self.assertEqual(404, response.status_code)
        return response

    def apply_filter(self, url, _filter, result):
        """
        Tests API filtering functionality.

        :param str url: API endpoint URL
        :param dict _filter: Filter parameters to apply
        :param list result: Expected filtered results
        """
        # we take out the potential query (e.g., ?param=1) arguments inside the url
        get_with_opts = lambda data: self.client.get(
            url.split("?")[0],
            follow_redirects=True,
            query_string=data,
            headers=self.get_header_with_auth(self.token),
        )
        response = get_with_opts(_filter)
        self.assertEqual(len(response.json), len(result))
        for k, v in enumerate(result):
            self.assertEqual(response.json[k], v)
        return

    def repr_method(self, idx, representation):
        """
        Tests the string representation of a model instance.

        :param int idx: ID of the model instance
        :param str representation: Expected string representation
        """
        row = self.model.query.get(idx)
        self.assertEqual(repr(row), representation)

    def str_method(self, idx, string: str):
        """
        Tests the string conversion of a model instance.

        :param int idx: ID of the model instance
        :param str string: Expected string value
        """
        row = self.model.query.get(idx)
        self.assertEqual(str(row), string)

    def cascade_delete(
        self, url, model, payload, url_2, model_2, payload_2, parent_key
    ):
        """
        Tests cascade deletion functionality between related models.

        :param str url: Parent model API endpoint
        :param class model: Parent model class
        :param dict payload: Parent model data
        :param str url_2: Child model API endpoint
        :param class model_2: Child model class
        :param dict payload_2: Child model data
        :param str parent_key: Foreign key field linking child to parent
        """
        parent_object_idx = self.create_new_row(url, model, payload)
        payload_2[parent_key] = parent_object_idx
        child_object_idx = self.create_new_row(url_2, model_2, payload_2)

        parent_object = model.query.get(parent_object_idx)
        child_object = model_2.query.get(child_object_idx)
        self.assertIsNotNone(parent_object)
        self.assertIsNotNone(child_object)

        parent_object.delete()

        parent_object = model.query.get(parent_object_idx)
        child_object = model_2.query.get(child_object_idx)
        self.assertIsNone(parent_object)
        self.assertIsNone(child_object)


class BaseTestCases:
    """
    Container class for common test case scenarios.
    """

    class ListFilters(CustomTestCase):
        """
        Test cases for list endpoint filtering functionality.
        """

        def setUp(self):
            """
            Sets up the test environment for filter tests.
            """
            super().setUp()
            self.payload = None

        def test_opt_filters_limit(self):
            """
            Tests the limit filter option.
            """
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(limit=1), [allrows.json[0]])

        def test_opt_filters_limit_none(self):
            """
            Tests the limit filter option
            """
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(limit=None), allrows.json)

        def test_opt_filters_offset(self):
            """
            Tests the offset filter option.
            """
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(offset=1, limit=2), allrows.json[1:3])

        def test_opt_filters_offset_zero(self):
            """
            Tests the offset filter option with a zero value.
            """
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(offset=0), allrows.json)

        def test_opt_filters_offset_none(self):
            """
            Tests the offset filter option with a None value.
            """
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(offset=None), allrows.json)

        def test_opt_filters_schema(self):
            """
            Tests the schema filter option.
            """
            # (we patch the request to airflow to check if the schema is valid)
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]

            self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(schema="timer"), [])

        def test_opt_filters_date_lte(self):
            """
            Tests the less than or equal to date filter.
            """
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)

            a = date_from_str(allrows.json[0]["created_at"])
            b = date_from_str(allrows.json[1]["created_at"])
            date_limit = b + (a - b) / 2
            # we ask for one before the last one => we get the second from the last
            self.apply_filter(
                self.url,
                dict(creation_date_lte=date_limit.isoformat(), limit=1),
                [allrows.json[1]],
            )

        def test_opt_filters_date_gte(self):
            """
            Tests the greater than or equal to date filter.
            """
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)

            date_limit = date_from_str(allrows.json[2]["created_at"]) + timedelta(
                microseconds=1
            )
            # we ask for all after the third from the last => we get the last two
            self.apply_filter(
                self.url,
                dict(creation_date_gte=date_limit.isoformat()),
                allrows.json[:2],
            )
            return

    class DetailEndpoint(CustomTestCase):
        """
        Test cases for detail endpoint functionality.
        """

        def setUp(self):
            """
            Sets up the test environment for detail endpoint tests.
            """
            super().setUp()
            self.payload = None
            self.response_items = None
            self.query_arguments = None

        def url_with_query_arguments(self):
            """
            Constructs URL with query arguments.

            :returns: URL with query parameters
            :rtype: str
            """
            if self.query_arguments is None:
                return self.url
            else:
                return (
                    self.url
                    + "?"
                    + "&".join(["%s=%s" % _ for _ in self.query_arguments.items()])
                )

        def test_get_one_row(self):
            """
            Tests retrieving a single row.
            """
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            payload = {**self.payload, **dict(id=idx)}
            payload["indicators"] = ""
            result = self.get_one_row(self.url + str(idx) + "/", payload)
            diff = self.response_items.symmetric_difference(result.keys())
            self.assertEqual(len(diff), 0)

        def test_get_one_row_superadmin(self):
            """
            Tests retrieving a single row as superadmin.
            """
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            token = self.create_service_user()
            self.get_one_row(
                self.url + str(idx) + "/", {**self.payload, **dict(id=idx)}, token=token
            )

        def test_get_nonexistent_row(self):
            """
            Tests attempting to retrieve a non-existent row.
            """
            self.get_one_row(
                self.url + "500" + "/", {}, expected_status=404, check_payload=False
            )

        def test_update_one_row(self):
            """
            Tests updating a single row.
            """
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            payload = {**self.payload, **dict(id=idx, name="new_name")}
            self.update_row(
                self.url + str(idx) + "/",
                dict(name="new_name"),
                payload,
            )

        def test_update_one_row_bad_format(self):
            """
            Tests updating a row with invalid format.
            """
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            self.update_row(
                self.url + str(idx) + "/",
                dict(id=10),
                {},
                expected_status=400,
                check_payload=False,
            )

            self.update_row(
                self.url + str(idx) + "/",
                dict(data_hash=""),
                {},
                expected_status=400,
                check_payload=False,
            )

        def test_delete_one_row(self):
            """
            Tests deleting a single row.
            """
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            self.delete_row(self.url + str(idx) + "/")

        # TODO: move to base endpoint custom class
        def test_incomplete_payload(self):
            """
            Tests creating a row with incomplete payload.
            """
            payload = {"description": "arg"}
            self.create_new_row(
                self.url_with_query_arguments(),
                self.model,
                payload,
                expected_status=400,
                check_payload=False,
            )

        # TODO: move to base endpoint custom class
        def test_payload_bad_format(self):
            """
            Tests creating a row with invalid payload format.
            """
            payload = {"name": 1}
            self.create_new_row(
                self.url_with_query_arguments(),
                self.model,
                payload,
                expected_status=400,
                check_payload=False,
            )


class CheckTokenTestCase:
    """
    Container class for token validation test cases.
    """

    class TokenEndpoint(TestCase):
        """
        Test cases for token endpoint functionality.
        """

        def create_app(self):
            """
            Creates test application instance.

            :returns: Test Flask application
            :rtype: Flask
            """
            app = create_app("testing")
            return app

        def setUp(self):
            """
            Sets up test environment for token tests.
            """
            db.create_all()
            self.data = None
            self.token = None
            self.response = None

        def tearDown(self):
            """
            Cleans up test environment after token tests.
            """
            db.session.remove()
            db.drop_all()

        def get_check_token(self):
            """
            Tests token validation endpoint.
            """
            if self.token:
                self.response = self.client.get(
                    TOKEN_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )
            else:
                self.response = self.client.get(
                    TOKEN_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                    },
                )


class LoginTestCases:
    """
    Container class for login-related test cases.
    """

    class LoginEndpoint(TestCase):
        """
        Test cases for login endpoint functionality.
        """

        def create_app(self):
            """
            Creates test application instance.

            :returns: Test Flask application
            :rtype: Flask
            """
            app = create_app("testing")
            return app

        def setUp(self):
            """
            Sets up test environment for login tests.
            """
            log.root.setLevel(current_app.config["LOG_LEVEL"])
            db.create_all()
            self.data = None
            self.response = None

        def tearDown(self):
            """
            Cleans up test environment after login tests.
            """
            db.session.remove()
            db.drop_all()

        def test_successful_log_in(self):
            """
            Tests successful login attempt.
            """
            payload = self.data

            self.response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            self.assertEqual(200, self.response.status_code)
            self.assertEqual(str, type(self.response.json["token"]))

        def test_validation_error(self):
            """
            Tests login with invalid data.
            """
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

        def test_missing_username(self):
            """
            Tests login with missing username.
            """
            payload = self.data
            payload.pop("username", None)
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            self.assertEqual(400, response.status_code)
            self.assertEqual(str, type(response.json["error"]))

        def test_missing_password(self):
            """
            Tests login with missing password.
            """
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

        def test_invalid_username(self):
            """
            Tests login with invalid username.
            """
            payload = self.data
            payload["username"] = "invalid_username"

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
            """
            Tests login with invalid password.
            """
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

        def test_old_token(self):
            """
            Tests using an expired token.
            """
            # First log in to get a valid user
            payload = self.data
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )
            self.idx = response.json["id"]

            # Generate an expired token
            expired_payload = {
                # Token expired 1 hour ago
                "exp": datetime.utcnow() - timedelta(hours=1),
                # Token created 2 hours ago
                "iat": datetime.utcnow() - timedelta(hours=2),
                "sub": self.idx,
                "iss": INTERNAL_TOKEN_ISSUER,
            }
            expired_token = jwt.encode(
                expired_payload,
                current_app.config["SECRET_TOKEN_KEY"],
                algorithm="HS256",
            )

            # Try to use the expired token
            response = self.client.get(
                USER_URL + str(self.idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {expired_token}",
                },
            )

            self.assertEqual(400, response.status_code)
            self.assertEqual(
                "The token has expired, please login again", response.json["error"]
            )

        def test_bad_format_token(self):
            """
            Tests using a malformed token.
            """
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(self.data),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            token = response.json["token"]
            self.idx = response.json["id"]

            response = self.client.get(
                USER_URL + str(self.idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer" + token,
                },
            )
            self.assertEqual(400, response.status_code)

        def test_invalid_token(self):
            """
            Tests using an invalid token.
            """
            # First log in to get a valid user
            payload = self.data
            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )
            self.idx = response.json["id"]

            # Generate an invalid token with wrong issuer
            invalid_payload = {
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
                "sub": self.idx,
                "iss": "invalid_issuer",
            }
            invalid_token = jwt.encode(
                invalid_payload,
                current_app.config["SECRET_TOKEN_KEY"],
                algorithm="HS256",
            )

            # Try to use the invalid token
            response = self.client.get(
                USER_URL + str(self.idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {invalid_token}",
                },
            )

            self.assertEqual(400, response.status_code)
            self.assertEqual(
                "Invalid token format or signature",
                response.json["error"],
            )

        def test_token(self):
            """
            Tests token generation and validation.
            """
            payload = self.data

            self.response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            self.assertEqual(200, self.response.status_code)
            self.assertEqual(str, type(self.response.json["token"]))
            decoded_token = jwt.decode(
                self.response.json["token"],
                current_app.config["SECRET_TOKEN_KEY"],
                algorithms="HS256",
            )

            self.assertAlmostEqual(
                datetime.now(timezone.utc),
                datetime.fromtimestamp(decoded_token["iat"], timezone.utc),
                delta=timedelta(seconds=2),
            )
