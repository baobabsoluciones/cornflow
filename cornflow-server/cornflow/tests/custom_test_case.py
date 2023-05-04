"""
This file contains the different custom test classes used to generalize the unit testing of cornflow.
"""

# Import from libraries
import logging as log
from datetime import datetime, timedelta
from flask import current_app
from flask_testing import TestCase
import json
import jwt

# Import from internal modules
from cornflow.app import create_app
from cornflow.models import UserRoleModel
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.shared.authentication import Auth
from cornflow.shared.const import ADMIN_ROLE, PLANNER_ROLE, SERVICE_ROLE
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
    def create_app(self):
        app = create_app("testing")
        return app

    @staticmethod
    def load_file(_file, fk=None, fk_id=None):
        with open(_file) as f:
            temp = json.load(f)
        if fk is not None and fk_id is not None:
            temp[fk] = fk_id
        return temp

    def setUp(self):
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

        self.user = Auth.return_user_from_token(self.token)
        self.url = None
        self.model = None
        self.copied_items = set()
        self.items_to_check = []
        self.roles_with_access = []

    @staticmethod
    def get_header_with_auth(token):
        return {"Content-Type": "application/json", "Authorization": "Bearer " + token}

    def create_user(self, data):
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

    @staticmethod
    def assign_role(user_id, role_id):

        if UserRoleModel.check_if_role_assigned(user_id, role_id):
            user_role = UserRoleModel.query.filter_by(
                user_id=user_id, role_id=role_id
            ).first()
        else:
            user_role = UserRoleModel({"user_id": user_id, "role_id": role_id})
            user_role.save()
        return user_role

    def create_role_endpoint(self, user_id, role_id, token):
        return self.client.post(
            USER_ROLE_URL,
            data=json.dumps({"user_id": user_id, "role_id": role_id}),
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

    def create_user_with_role(self, role_id):
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
        return self.create_user_with_role(SERVICE_ROLE)

    def create_admin(self):
        return self.create_user_with_role(ADMIN_ROLE)

    def create_planner(self):
        return self.create_user_with_role(PLANNER_ROLE)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_new_row(
        self, url, model, payload, expected_status=201, check_payload=True, token=None
    ):
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

    def get_rows(self, url, data, token=None, check_data=True):
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
                for key in self.get_keys_to_check(data[i]):
                    self.assertIn(key, rows_data[i])
                    if key in data[i]:
                        self.assertEqual(rows_data[i][key], data[i][key])
        return rows

    def get_keys_to_check(self, payload):
        if len(self.items_to_check):
            return self.items_to_check
        return payload.keys()

    def get_one_row(
        self, url, payload, expected_status=200, check_payload=True, token=None
    ):
        token = token or self.token

        row = self.client.get(
            url, follow_redirects=True, headers=self.get_header_with_auth(token)
        )

        self.assertEqual(expected_status, row.status_code)
        if not check_payload:
            return row.json
        self.assertEqual(row.json["id"], payload["id"])
        for key in self.get_keys_to_check(payload):
            self.assertIn(key, row.json)
            if key in payload:
                self.assertEqual(row.json[key], payload[key])
        return row.json

    def get_no_rows(self, url, token=None):
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
        row = self.model.query.get(idx)
        self.assertEqual(repr(row), representation)

    def str_method(self, idx, string: str):
        row = self.model.query.get(idx)
        self.assertEqual(str(row), string)

    def cascade_delete(
        self, url, model, payload, url_2, model_2, payload_2, parent_key
    ):
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
    class ListFilters(CustomTestCase):
        def setUp(self):
            super().setUp()
            self.payload = None

        def test_opt_filters_limit(self):
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(limit=1), [allrows.json[0]])

        def test_opt_filters_offset(self):
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(offset=1, limit=2), allrows.json[1:3])

        def test_opt_filters_schema(self):
            # (we patch the request to airflow to check if the schema is valid)
            # we create 4 instances
            data_many = [self.payload for _ in range(4)]
            data_many[-1] = {**data_many[-1], **dict(schema="timer")}
            allrows = self.get_rows(self.url, data_many)
            self.apply_filter(self.url, dict(schema="timer"), allrows.json[:1])

        def test_opt_filters_date_lte(self):
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
        def setUp(self):
            super().setUp()
            self.payload = None
            self.response_items = None
            self.query_arguments = None

        def url_with_query_arguments(self):
            if self.query_arguments is None:
                return self.url
            else:
                return (
                    self.url
                    + "?"
                    + "&".join(["%s=%s" % _ for _ in self.query_arguments.items()])
                )

        def test_get_one_row(self):
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            payload = {**self.payload, **dict(id=idx)}
            payload["indicators"] = ""
            result = self.get_one_row(self.url + str(idx) + "/", payload)
            diff = self.response_items.symmetric_difference(result.keys())
            self.assertEqual(len(diff), 0)

        def test_get_one_row_superadmin(self):
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            token = self.create_service_user()
            self.get_one_row(
                self.url + str(idx) + "/", {**self.payload, **dict(id=idx)}, token=token
            )

        def test_get_nonexistent_row(self):
            self.get_one_row(
                self.url + "500" + "/", {}, expected_status=404, check_payload=False
            )

        def test_update_one_row(self):
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
            idx = self.create_new_row(
                self.url_with_query_arguments(), self.model, self.payload
            )
            self.delete_row(self.url + str(idx) + "/")

        # TODO: move to base endpoint custom class
        def test_incomplete_payload(self):
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
            payload = {"name": 1}
            self.create_new_row(
                self.url_with_query_arguments(),
                self.model,
                payload,
                expected_status=400,
                check_payload=False,
            )


class CheckTokenTestCase:
    class TokenEndpoint(TestCase):
        def create_app(self):
            app = create_app("testing")
            return app

        def setUp(self):
            db.create_all()
            self.data = None
            self.token = None
            self.response = None

        def tearDown(self):
            db.session.remove()
            db.drop_all()

        def get_check_token(self):
            if self.token:
                self.response = self.client.get(
                    TOKEN_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
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
    class LoginEndpoint(TestCase):
        def create_app(self):
            app = create_app("testing")
            return app

        def setUp(self):
            log.root.setLevel(current_app.config["LOG_LEVEL"])
            db.create_all()
            self.data = None
            self.response = None

        def tearDown(self):
            db.session.remove()
            db.drop_all()

        def test_successful_log_in(self):
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
            token = (
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1MzYwNjUsImlhdCI6MTYxMDQ0OTY2NSwic3ViIjoxfQ"
                ".QEfmO-hh55PjtecnJ1RJT3aW2brGLadkg5ClH9yrRnc "
            )

            payload = self.data

            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            self.idx = response.json["id"]

            response = self.client.get(
                USER_URL + str(self.idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            )

            self.assertEqual(400, response.status_code)
            self.assertEqual(
                "The token has expired, please login again", response.json["error"]
            )

        def test_bad_format_token(self):
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
            token = (
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTA1Mzk5NTMsImlhdCI6MTYxMDQ1MzU1Mywic3ViIjoxfQ"
                ".g3Gh7k7twXZ4K2MnQpgpSr76Sl9VX6TkDWusX5YzImo"
            )

            payload = self.data

            response = self.client.post(
                LOGIN_URL,
                data=json.dumps(payload),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )
            self.idx = response.json["id"]

            response = self.client.get(
                USER_URL + str(self.idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            )

            self.assertEqual(400, response.status_code)
            self.assertEqual(
                "Invalid token, please try again with a new token",
                response.json["error"],
            )

        def test_token(self):
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
                current_app.config["SECRET_KEY"],
                algorithms="HS256",
            )

            self.assertAlmostEqual(
                datetime.utcnow(),
                datetime.utcfromtimestamp(decoded_token["iat"]),
                delta=timedelta(seconds=2),
            )
