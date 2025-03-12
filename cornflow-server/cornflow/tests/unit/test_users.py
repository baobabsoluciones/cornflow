"""
Unit tests for the user endpoints.

This module contains tests for the user-related functionalities, including:
- User authentication and authorization
- User role management
- Password handling and rotation
- User profile operations

All tests follow a consistent pattern of setting up test data,
executing operations, and verifying results against expected outcomes.
"""

import json
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import (
    CaseModel,
    ExecutionModel,
    InstanceModel,
    PermissionsDAG,
    UserModel,
    UserRoleModel,
)
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE, PLANNER_ROLE, VIEWER_ROLE
from cornflow.tests.const import (
    CASE_PATH,
    CASE_URL,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    INSTANCE_PATH,
    INSTANCE_URL,
    LOGIN_URL,
    SIGNUP_URL,
    USER_URL,
)


class TestUserEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.url = USER_URL
        self.model = UserModel

        self.viewer = dict(
            username="aViewer", email="viewer@test.com", password="Testpassword1!"
        )

        self.planner = dict(
            username="aPlanner",
            email="test@test.com",
            password="Testpassword1!",
            first_name="first_planner",
            last_name="last_planner",
        )

        self.planner_2 = dict(
            username="aSecondPlanner", email="test2@test.com", password="Testpassword2!"
        )

        self.admin = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        self.admin_2 = dict(
            username="aSecondAdmin",
            email="admin2@admin2.com",
            password="Testpassword2!",
        )

        self.service_user = dict(
            username="aServiceUser",
            email="service_user@test.com",
            password="Tpass_service_user1",
        )

        self.login_keys = ["username", "password"]
        self.items_to_check = ["email", "username", "id"]
        self.modifiable_items = [
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
        ]

        self.payloads = [
            self.viewer,
            self.planner,
            self.planner_2,
            self.admin,
            self.admin_2,
            self.service_user,
        ]

        for u_data in self.payloads:

            response = self.client.post(
                SIGNUP_URL,
                data=json.dumps(u_data),
                follow_redirects=True,
                headers={"Content-Type": "application/json"},
            )

            u_data["id"] = response.json["id"]

            if "viewer" in u_data["email"]:
                user_role = UserRoleModel(
                    {"user_id": u_data["id"], "role_id": VIEWER_ROLE}
                )
                user_role.save()

                UserRoleModel.query.filter_by(
                    user_id=u_data["id"], role_id=PLANNER_ROLE
                ).delete()
                db.session.commit()

            if "admin" in u_data["email"]:
                user_role = UserRoleModel(
                    {"user_id": u_data["id"], "role_id": ADMIN_ROLE}
                )
                user_role.save()

            if "service_user" in u_data["email"]:
                user_role = UserRoleModel(
                    {"user_id": u_data["id"], "role_id": SERVICE_ROLE}
                )
                user_role.save()

        db.session.commit()
        register_dag_permissions_command(verbose=False)

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

    def get_non_existing_user(self):
        pass

    def make_admin(self, user_asks, user_asked, make_admin=1):
        token = self.log_in(user_asks).json["token"]
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
        token = self.log_in(user_asks).json["token"]

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
        token = self.log_in(user_asks).json["token"]
        url = "{}{}/".format(self.url, user_asked["id"])
        return self.client.delete(
            url,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

    def test_get_all_users_service_user(self):
        # the service role should not be able to get the users
        response = self.get_user(self.service_user)
        self.assertEqual(403, response.status_code)

    def test_get_all_users_user(self):
        # a simple user should not be able to do it
        response = self.get_user(self.planner)
        self.assertEqual(403, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_all_users_admin(self):
        # An admin should be able to get all users
        response = self.get_user(self.admin)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(response.json), len(self.payloads))

    def test_get_same_user(self):
        # if a user asks for itself: it's ok
        for u_data in [self.planner, self.admin, self.service_user]:
            response = self.get_user(u_data, u_data)
            self.assertEqual(200, response.status_code)
            for item in self.items_to_check:
                self.assertEqual(response.json[item], u_data[item])

    def test_get_another_user(self):
        response = self.get_user(self.planner, self.admin)
        self.assertEqual(400, response.status_code)
        self.assertTrue("error" in response.json)

    def test_get_another_user_admin(self):
        response = self.get_user(self.admin, self.planner)
        self.assertEqual(200, response.status_code)
        for item in self.items_to_check:
            self.assertEqual(response.json[item], self.planner[item])

    def test_user_makes_someone_admin(self):
        response = self.make_admin(self.planner, self.planner)
        self.assertEqual(403, response.status_code)

    def test_service_user_makes_someone_admin(self):
        response = self.make_admin(self.service_user, self.planner)
        self.assertEqual(403, response.status_code)

    def test_admin_makes_someone_admin(self):
        response = self.make_admin(self.admin, self.planner)
        self.assertEqual(200, response.status_code)
        self.assertEqual(True, UserRoleModel.is_admin(self.planner["id"]))

    def test_admin_takes_someone_admin(self):
        response = self.make_admin(self.admin, self.admin_2, 0)
        self.assertEqual(200, response.status_code)
        self.assertEqual(False, UserRoleModel.is_admin(self.planner["id"]))

    def test_user_deletes_admin(self):
        response = self.delete_user(self.planner, self.admin)
        self.assertEqual(403, response.status_code)

    def test_admin_deletes_service_user(self):
        response = self.delete_user(self.admin, self.service_user)
        self.assertEqual(403, response.status_code)

    def test_admin_deletes_user(self):
        response = self.delete_user(self.admin, self.planner)
        self.assertEqual(200, response.status_code)
        response = self.get_user(self.admin, self.planner)
        self.assertEqual(404, response.status_code)

    def test_service_user_deletes_admin(self):
        response = self.delete_user(self.service_user, self.admin)
        self.assertEqual(403, response.status_code)

    def test_edit_info(self):
        payload = {
            "email": "newtest@test.com",
            "first_name": "FirstName",
            "last_name": "LastName",
        }

        self.modifiable_items = ["email", "first_name", "last_name"]

        response = self.modify_info(self.planner, self.planner, payload)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Updated correctly", response.json["message"])

        response = self.get_user(self.planner, self.planner)
        self.assertEqual(200, response.status_code)

        for item in self.modifiable_items:
            if item != "password":
                self.assertEqual(response.json[item], payload[item])
                self.assertNotEqual(response.json[item], self.planner[item])

    def test_admin_edit_info(self):
        payload = {
            "username": "newtestname",
            "email": "newtest@test.com",
            "first_name": "FirstName",
            "last_name": "LastName",
        }

        response = self.modify_info(self.admin, self.planner, payload)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Updated correctly", response.json["message"])

        response = self.get_user(self.admin, self.planner)
        self.assertEqual(200, response.status_code)

        for item in self.modifiable_items:
            if item != "password":
                self.assertEqual(response.json[item], payload[item])
                self.assertNotEqual(response.json[item], self.planner[item])

    def test_edit_other_user_info(self):
        payload = {"username": "newtestname", "email": "newtest@test.com"}
        response = self.modify_info(self.planner_2, self.planner, payload)
        self.assertEqual(403, response.status_code)

    def test_change_password(self):
        payload = {"password": "Newtestpassword1!"}
        response = self.modify_info(self.planner, self.planner, payload)
        self.assertEqual(200, response.status_code)
        self.planner["password"] = payload["password"]
        response = self.log_in(self.planner)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])

    def test_change_other_user_password(self):
        payload = {"password": "Newtestpassword_2"}
        response = self.modify_info(self.planner_2, self.planner, payload)
        self.assertEqual(403, response.status_code)

    def test_admin_change_password(self):
        payload = {"password": "Newtestpassword_3"}
        response = self.modify_info(self.admin, self.planner, payload)
        self.assertEqual(200, response.status_code)
        self.planner["password"] = payload["password"]
        response = self.log_in(self.planner)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])

    def test_service_user_change_password(self):
        payload = {"password": "Newtestpassword_4"}
        response = self.modify_info(self.service_user, self.planner, payload)
        self.assertEqual(403, response.status_code)

    def test_viewer_user_change_password(self):
        payload = {"password": "Newtestpassword_5"}
        response = self.modify_info(self.viewer, self.viewer, payload)
        self.assertEqual(200, response.status_code)
        self.viewer["password"] = payload["password"]
        response = self.log_in(self.viewer)
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.json["token"])

    def test_change_password_rotation(self):
        current_app.config["PWD_ROTATION_TIME"] = 1  # in days
        payload = {"pwd_last_change": (datetime.now(timezone.utc) - timedelta(days=2))}

        planner = UserModel.get_one_user(self.planner["id"])
        planner.update(payload)

        response = self.log_in(self.planner)
        self.assertEqual(True, response.json["change_password"])

        payload = {"password": "Newtestpassword1!"}
        self.modify_info(self.planner, self.planner, payload)
        self.planner.update(payload)

        response = self.log_in(self.planner)
        self.assertEqual(False, response.json["change_password"])


class TestUserModel(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)

        self.url = USER_URL
        self.model = UserModel

        self.admin = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.admin),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.admin["id"] = response.json["id"]

        user_role = UserRoleModel({"user_id": self.admin["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        self.login_keys = ["username", "password"]

        self.viewer = dict(
            username="aViewer", email="viewer@test.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.viewer),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.viewer["id"] = response.json["id"]
        register_dag_permissions_command(verbose=False)

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

    def test_instance_delete_cascade(self):
        response = self.log_in(self.admin)
        token = response.json["token"]
        user_id = response.json["id"]
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)

        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(201, response.status_code)
        instance_id = response.json["id"]

        response = self.client.delete(
            self.url + str(user_id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)

        instance = InstanceModel.query.get(instance_id)
        self.assertIsNone(instance)

    def test_instance_execution_delete_cascade(self):
        response = self.log_in(self.admin)
        token = response.json["token"]
        user_id = response.json["id"]
        with open(INSTANCE_PATH) as f:
            payload = json.load(f)

        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(201, response.status_code)
        instance_id = response.json["id"]

        with open(EXECUTION_PATH) as f:
            payload = json.load(f)

        payload["instance_id"] = instance_id
        response = self.client.post(
            EXECUTION_URL_NORUN,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(201, response.status_code)
        execution_id = response.json["id"]

        response = self.client.delete(
            self.url + str(user_id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)

        instance = InstanceModel.query.get(instance_id)
        execution = ExecutionModel.query.get(execution_id)
        self.assertIsNone(instance)
        self.assertIsNone(execution)

    def test_case_delete_cascade(self):
        response = self.log_in(self.admin)
        token = response.json["token"]
        user_id = response.json["id"]
        with open(CASE_PATH) as f:
            payload = json.load(f)

        response = self.client.post(
            CASE_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(201, response.status_code)
        case_id = response.json["id"]

        response = self.client.delete(
            self.url + str(user_id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)

        case = CaseModel.query.get(case_id)
        self.assertIsNone(case)

    def test_user_role_delete_cascade(self):
        response = self.log_in(self.admin)
        token = response.json["token"]
        user_id = response.json["id"]

        user_role = UserRoleModel.query.filter_by(user_id=user_id).first()

        self.assertIsNotNone(user_role)

        response = self.client.delete(
            self.url + str(user_id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)

        user_role = UserRoleModel.query.filter_by(user_id=user_id).first()
        self.assertIsNone(user_role)

    def test_user_roles(self):
        response = self.log_in(self.admin)
        user_id = response.json["id"]
        user = UserModel.query.get(user_id)
        self.assertEqual(user.roles, {2: "planner", 3: "admin"})

    def test_user_no_roles(self):
        role = UserRoleModel.query.filter_by(user_id=self.viewer["id"]).delete()
        user = UserModel.query.get(self.viewer["id"])
        self.assertEqual(user.roles, {})

    def test_permission_dag_cascade(self):
        response = self.log_in(self.admin)
        token = response.json["token"]
        user_id = response.json["id"]

        before = PermissionsDAG.get_user_dag_permissions(user_id)
        self.assertIsNotNone(before)
        response = self.client.delete(
            self.url + str(user_id) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)
        after = PermissionsDAG.get_user_dag_permissions(user_id)
        self.assertEqual([], after)
        self.assertNotEqual(before, after)


"""class TestRecoverPasswordEndpoint(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        AccessInitialization().run()

        self.url = USER_URL
        self.model = UserModel

        self.user = dict(
            username="aViewer", email="cornflow.user.test@gmail.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.user),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.user["id"] = response.json["id"]
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_recover_password_valid_address(self):
        response = self.client.put(
            RECOVER_PASSWORD_URL,
            data=json.dumps(dict(email=self.user["email"])),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.pop("email")
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps(self.user),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual(str, type(response.json["error"]))

    def test_recover_password_inexistant_address(self):
        response = self.client.put(
            RECOVER_PASSWORD_URL,
            data=json.dumps(dict(email="invalid.viewer@test.com")),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
"""
