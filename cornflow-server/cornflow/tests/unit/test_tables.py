"""
Unit test for the instances endpoints
"""

# Import from libraries
import json
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.models import UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE, DATA_DOES_NOT_EXIST_MSG
from cornflow.tests.const import LOGIN_URL, SIGNUP_URL, TABLES_URL


class TestTablesListEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
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

        user_role = UserRoleModel(
            {"user_id": self.service_user["id"], "role_id": ADMIN_ROLE}
        )
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
            "created_at",
            "deleted_at",
            "email",
            "first_name",
            "id",
            "last_name",
            "password",
            "updated_at",
            "username",
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
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json), 1)
        usernames = [user["username"] for user in response.json]
        self.assertIn(self.service_user["username"], usernames)
        for key in self.keys_to_check:
            self.assertIn(key, response.json[0].keys())

    def test_get_with_filters(self):
        for i in range(4):
            # Create new users to there are at least 5 in the table
            new_user = dict(
                username=f"user{i}",
                email=f"user{i}@user.com",
                password="Testpassword1!",
            )

            self.client.post(
                SIGNUP_URL,
                data=json.dumps(new_user),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )
        response = self.client.get(
            self.url + self.table + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            query_string=dict(limit=3),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)


class TestTablesDetailEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
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

        user_role = UserRoleModel(
            {"user_id": self.service_user["id"], "role_id": ADMIN_ROLE}
        )
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
            "created_at",
            "deleted_at",
            "email",
            "first_name",
            "id",
            "last_name",
            "password",
            "updated_at",
            "username",
        ]

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_one_table(self):
        user = self.service_user

        response = self.client.get(
            self.url + self.table + f"/{user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        self.assertEqual(response.status_code, 200)
        for key in self.keys_to_check:
            self.assertIn(key, response.json.keys())
            if key in user and key != "password":
                self.assertEqual(response.json[key], user[key])

    def test_get_one_table_invalid_id(self):
        # String id, while it should be an integer for that table
        response = self.client.get(
            self.url + self.table + f"/abcd/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
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
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], DATA_DOES_NOT_EXIST_MSG)


class TestTablesEndpointAdmin(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
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
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json["error"], "You do not have permission to access this endpoint"
        )

    def test_get_one_table(self):
        response = self.client.get(
            self.url + self.table + f"/{self.user['id']}/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json["error"], "You do not have permission to access this endpoint"
        )
