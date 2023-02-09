"""
Unit test for the instances endpoints
"""

# Import from libraries
import json
from flask_testing import TestCase
import sys
import os

prev_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..")
print(prev_dir)
sys.path.insert(1, prev_dir)

# Import from internal modules
from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE
from cornflow.models import UserModel, UserRoleModel
from cornflow_core.shared import db
from cornflow.tests.const import (
    LOGIN_URL,
    SIGNUP_URL,
    TABLES_URL
)


class TestTablesListEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(0)
        self.service_user = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.service_user),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        data = dict(self.service_user)
        data.pop("email")
        self.service_user["id"] = response.json["id"]

        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        user_role = UserRoleModel({"user_id": self.service_user["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        user_role = UserRoleModel(
            {"user_id": self.service_user["id"], "role_id": SERVICE_ROLE}
        )
        user_role.save()
        db.session.commit()

        self.url = TABLES_URL
        self.table = "users"
        self.keys_to_check = [
            'created_at',
            'deleted_at',
            'email',
            'first_name',
            'id',
            'last_name',
            'password',
            'updated_at',
            'username'
        ]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_table(self):
        response = self.client.get(
            self.url + self.table + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json), 1)
        usernames = [user["username"] for user in response.json]
        self.assertIn(self.service_user["username"], usernames)
        for key in self.keys_to_check:
            self.assertIn(key, response.json[0].keys())

    def test_post_table(self):
        payload = dict(
            data=dict(
                username=f"AnotherUser",
                password="TestPassword1!",
                email=f"testuser@cornflow.com"
            )
        )
        response = self.client.post(
            self.url + self.table + "/",
            follow_redirects=True,
            data=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 201)
        for key in self.keys_to_check:
            self.assertIn(key, response.json.keys())
            if key in payload["data"] and key != "password":
                self.assertEqual(response.json[key], payload["data"][key])

        response = self.client.get(
            self.url + self.table + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        all_usernames = [user["username"] for user in response.json]
        self.assertIn(payload["data"]["username"], all_usernames)

    def test_post_table_invalid_data(self):
        # Username missing
        payload = dict(
            data=dict(
                password="TestPassword1!",
                email=f"testuser@cornflow.com"
            )
        )
        response = self.client.post(
            self.url + self.table + "/",
            follow_redirects=True,
            data=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Integrity error on saving with data <Username None>")


class TestTablesDetailEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(0)
        self.service_user = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.service_user),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        data = dict(self.service_user)
        data.pop("email")
        self.service_user["id"] = response.json["id"]

        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        user_role = UserRoleModel({"user_id": self.service_user["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        user_role = UserRoleModel(
            {"user_id": self.service_user["id"], "role_id": SERVICE_ROLE}
        )
        user_role.save()
        db.session.commit()

        self.url = TABLES_URL
        self.table = "users"
        self.keys_to_check = [
            'created_at',
            'deleted_at',
            'email',
            'first_name',
            'id',
            'last_name',
            'password',
            'updated_at',
            'username'
        ]
        self.payload = dict(
            data=dict(
                username=f"AnotherUser",
                password="TestPassword1!",
                email=f"testuser@cornflow.com"
            )
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def post_one(self):
        return self.client.post(
            self.url + self.table + "/",
            follow_redirects=True,
            data=json.dumps(self.payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        ).json

    def test_get_one_table(self):
        user = self.post_one()

        response = self.client.get(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 200)
        for key in self.keys_to_check:
            self.assertIn(key, response.json.keys())
            if key in self.payload["data"] and key != "password":
                self.assertEqual(response.json[key], self.payload["data"][key])

    def test_get_one_table_invalid_id(self):
        # String id, while it should be an integer for that table
        response = self.client.get(
            self.url + self.table + f"/abcd/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Invalid identifier.")

        # Integer id that does not correspond to any user
        response = self.client.get(
            self.url + self.table + f"/12345/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "The object does not exist")

    def test_delete_one_table(self):
        user = self.post_one()

        response = self.client.delete(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "The object has been deleted")

        response = self.client.get(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json.get("error"), 'The object does not exist')

    def test_delete_one_table_invalid_id(self):
        # String id, while it should be an integer for that table
        response = self.client.delete(
            self.url + self.table + f"/abcd/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Invalid identifier.")

        # Integer id that does not correspond to any user
        response = self.client.get(
            self.url + self.table + f"/12345/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "The object does not exist")

    def test_put_one_table(self):
        user = self.post_one()

        payload = dict(
            data=dict(
                first_name="First-name"
            )
        )
        response = self.client.put(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "Updated correctly")

        response = self.client.get(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        for key in self.keys_to_check:
            self.assertIn(key, response.json.keys())
            if key in self.payload["data"] and key != "password":
                self.assertEqual(response.json[key], self.payload["data"][key])
            if key in payload["data"]:
                self.assertEqual(response.json[key], payload["data"][key])

    def test_put_one_table_invalid_id(self):
        # String id, while it should be an integer for that table
        response = self.client.put(
            self.url + self.table + f"/abcd/",
            follow_redirects=True,
            json=dict(data=dict()),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Invalid identifier.")

        # Integer id that does not correspond to any user
        response = self.client.get(
            self.url + self.table + f"/12345/",
            follow_redirects=True,
            json=dict(data=dict()),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "The object does not exist")

    def test_put_one_table_invalid_data(self):
        user = self.post_one()

        payload = dict(
            data=dict(
                username=None
            )
        )
        response = self.client.put(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Integrity error on updating with data <Username AnotherUser>")

        response = self.client.get(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertIsNotNone(response.json.get("username"))


class TestTablesEndpointAdmin(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(0)
        self.user = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.user),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        data = dict(self.user)
        data.pop("email")
        self.user["id"] = response.json["id"]

        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        user_role = UserRoleModel({"user_id": self.user["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        self.url = TABLES_URL
        self.table = "users"

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_table(self):
        response = self.client.get(
            self.url + self.table + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "You do not have permission to access this endpoint")

    def test_get_one_table(self):
        response = self.client.get(
            self.url + self.table + f"/{self.user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "You do not have permission to access this endpoint")
