import json

from flask_testing import TestCase
from cornflow.app import create_app
from cornflow.commands import SecurityInitialization
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared.const import DEFAULT_ROLE, ADMIN_ROLE, SUPER_ADMIN_ROLE
from cornflow.shared.utils import db
from cornflow.tests.const import USER_URL, LOGIN_URL, SIGNUP_URL


class TestUserEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        SecurityInitialization().run()

        self.url = USER_URL
        self.model = UserModel
        self.user = dict(
            name="testname",
            email="test@test.com",
            password="testpassword",
        )
        self.user_2 = dict(
            name="testname2",
            email="test2@test.com",
            password="testpassword2",
        )
        self.admin = dict(
            name="anAdminUser",
            email="admin@admin.com",
            password="testpassword",
        )
        self.super_admin = dict(
            name="anAdminSuperUser",
            email="super_admin@admin.com",
            password="tpass_super_admin",
        )
        self.login_keys = ["email", "password"]
        self.items_to_check = ["email", "name", "id"]
        self.modifiable_items = ["email", "name", "password"]

        for u_data in [self.user, self.user_2, self.admin, self.super_admin]:
            response = self.client.post(
                SIGNUP_URL,
                data=json.dumps(u_data),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            u_data["id"] = response.json["id"]

            if "admin" in u_data["email"]:
                user_role = UserRoleModel(
                    {"user_id": u_data["id"], "role_id": ADMIN_ROLE}
                )
                user_role.save()

            if "super_admin" in u_data["email"]:
                user_role = UserRoleModel(
                    {"user_id": u_data["id"], "role_id": SUPER_ADMIN_ROLE}
                )
                user_role.save()

        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def log_in(self, user):
        data = {k: user[k] for k in self.login_keys}
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

    def get_user(self, user_asks, user_asked=None):
        data = {k: user_asks[k] for k in self.login_keys}
        url = self.url
        if user_asked is not None:
            url += "{}/".format(user_asked["id"])
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]
        return self.client.get(
            url,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

    def get_nonexisting_user(self):
        pass

    def make_admin(self, user_asks, user_asked, make_admin=1):
        data = {k: user_asks[k] for k in self.login_keys}
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]
        url = "{}{}/{}/".format(self.url, user_asked["id"], make_admin)
        return self.client.put(
            url,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

    def modify_info(self, user_asks, user_asked, payload):
        data = {k: user_asks[k] for k in self.login_keys}
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        url = "{}{}/".format(self.url, user_asked["id"])
        return self.client.put(
            url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

    def delete_user(self, user_asks, user_asked):
        data = {k: user_asks[k] for k in self.login_keys}
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]
        url = "{}{}/".format(self.url, user_asked["id"])
        return self.client.delete(
            url,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

    def test_get_all_users_superadmin(self):
        # the superadmin should be able to list all users
        response = self.get_user(self.super_admin)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(response.json), 4)

    def test_get_all_users_user(self):
        # a simple user should not be able to do it
        response = self.get_user(self.user)
        self.assertEqual(403, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_all_users_admin(self):
        # an admin should not be able to do it
        response = self.get_user(self.admin)
        self.assertEqual(403, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_same_user(self):
        # if a user asks for itself: it's ok
        for u_data in [self.user, self.admin, self.super_admin]:
            response = self.get_user(u_data, u_data)
            self.assertEqual(200, response.status_code)
            for item in self.items_to_check:
                self.assertEqual(response.json[item], u_data[item])

    def test_get_another_user(self):
        response = self.get_user(self.user, self.admin)
        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_another_user_admin(self):
        response = self.get_user(self.admin, self.user)
        self.assertEqual(200, response.status_code)
        for item in self.items_to_check:
            self.assertEqual(response.json[item], self.user[item])

    # def test_user_makes_someone_admin(self):
    #     response = self.make_admin(self.user, self.user)
    #     self.assertEqual(400, response.status_code)
    #
    # def test_admin_makes_someone_admin(self):
    #     response = self.make_admin(self.admin, self.user)
    #     self.assertEqual(400, response.status_code)
    #
    # def test_super_admin_makes_someone_admin(self):
    #     response = self.make_admin(self.super_admin, self.user)
    #     self.assertEqual(201, response.status_code)
    #     for item in self.items_to_check:
    #         if item == "admin":
    #             self.assertTrue(response.json[item])
    #         else:
    #             self.assertEqual(response.json[item], self.user[item])
    #
    # def test_super_admin_takes_someone_admin(self):
    #     response = self.make_admin(self.super_admin, self.admin, 0)
    #     self.assertEqual(201, response.status_code)
    #     for item in self.items_to_check:
    #         if item == "admin":
    #             self.assertFalse(response.json[item])
    #         else:
    #             self.assertEqual(response.json[item], self.admin[item])

    def test_user_deletes_admin(self):
        response = self.delete_user(self.user, self.admin)
        self.assertEqual(403, response.status_code)

    def test_admin_deletes_superadmin(self):
        response = self.delete_user(self.admin, self.super_admin)
        self.assertEqual(403, response.status_code)

    def test_admin_deletes_user(self):
        response = self.delete_user(self.admin, self.user)
        self.assertEqual(200, response.status_code)
        response = self.get_user(self.admin, self.user)
        self.assertEqual(404, response.status_code)

    def test_superadmin_deletes_admin(self):
        response = self.delete_user(self.super_admin, self.admin)
        self.assertEqual(200, response.status_code)
        response = self.get_user(self.super_admin, self.admin)
        self.assertEqual(404, response.status_code)

    def test_edit_info(self):
        payload = {"name": "newtestname", "email": "newtest@test.com"}
        response = self.modify_info(self.user, self.user, payload)
        self.assertEqual(200, response.status_code)
        for item in self.modifiable_items:
            if item != "password":
                self.assertEqual(response.json[item], payload[item])
                self.assertNotEqual(response.json[item], self.user[item])

    def test_admin_edit_info(self):
        payload = {"name": "newtestname", "email": "newtest@test.com"}
        response = self.modify_info(self.admin, self.user, payload)
        self.assertEqual(200, response.status_code)
        for item in self.modifiable_items:
            if item != "password":
                self.assertEqual(response.json[item], payload[item])
                self.assertNotEqual(response.json[item], self.user[item])

    def test_edit_other_user_info(self):
        payload = {"name": "newtestname", "email": "newtest@test.com"}
        response = self.modify_info(self.user_2, self.user, payload)
        self.assertEqual(403, response.status_code)

    def test_change_password(self):
        payload = {"password": "newtestpassword"}
        response = self.modify_info(self.user, self.user, payload)
        self.assertEqual(200, response.status_code)
        self.user["password"] = payload["password"]
        response = self.log_in(self.user)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])

    def test_change_other_user_password(self):
        payload = {"password": "newtestpassword_2"}
        response = self.modify_info(self.user_2, self.user, payload)
        self.assertEqual(403, response.status_code)

    def test_admin_change_password(self):
        payload = {"password": "newtestpassword_3"}
        response = self.modify_info(self.admin, self.user, payload)
        self.assertEqual(200, response.status_code)
        self.user["password"] = payload["password"]
        response = self.log_in(self.user)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])

    def test_super_admin_change_password(self):
        payload = {"password": "newtestpassword_4"}
        response = self.modify_info(self.super_admin, self.user, payload)
        self.assertEqual(200, response.status_code)
        self.user["password"] = payload["password"]
        response = self.log_in(self.user)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])
