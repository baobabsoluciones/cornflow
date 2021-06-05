"""
Unit test for the role endpoints
"""

# Import from internal modules
from cornflow.endpoints import (
    RoleDetailEndpoint,
    RolesListEndpoint,
    UserRoleListEndpoint,
    UserRoleDetailEndpoint,
)
from cornflow.models import RoleModel, UserRoleModel
from cornflow.shared.const import BASE_ROLES, ADMIN_ROLE, VIEWER_ROLE
from cornflow.tests.const import ROLES_URL, USER_ROLE_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestRolesListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = {"name": "new_role"}
        self.payloads = [
            {"id": key, "name": value} for key, value in BASE_ROLES.items()
        ]
        self.url = ROLES_URL
        self.model = RoleModel
        self.items_to_check = ["name"]
        self.roles_with_access = RolesListEndpoint.ROLES_WITH_ACCESS

    def tearDown(self):
        super().tearDown()

    def test_get_roles_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertCountEqual(self.payloads, response.json)

    def test_get_no_roles(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )
                self.assertEqual(403, response.status_code)

    def test_new_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            self.payload["name"] += str(role)
            self.create_new_row(self.url, self.model, self.payload)

    def test_new_role_not_authorized(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                self.create_new_row(
                    self.url, self.model, {}, expected_status=403, check_payload=False
                )


class TestRolesDetailEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = ROLES_URL
        self.model = RoleModel
        self.items_to_check = ["id", "name"]
        self.roles_with_access = RoleDetailEndpoint.ROLES_WITH_ACCESS

    def test_get_one_role_authorized_user(self):
        for role in self.roles_with_access:
            token = self.create_user_with_role(role)

            response = self.client.get(
                self.url + str(VIEWER_ROLE) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            )

            self.assertEqual(200, response.status_code)

    def test_get_one_role_not_authorized(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url + str(VIEWER_ROLE) + "/",
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token,
                    },
                )

                self.assertEqual(403, response.status_code)

    def test_get_no_roles_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url + str(500) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )

            self.assertEqual(404, response.status_code)

    def test_modify_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            self.update_row(
                self.url + str(VIEWER_ROLE) + "/",
                dict(name="not-viewer" + str(role)),
                {"id": VIEWER_ROLE, "name": "not-viewer" + str(role)},
            )

    def test_modify_role_not_authorized(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                self.update_row(
                    self.url + str(VIEWER_ROLE) + "/",
                    dict(name="not-viewer" + str(role)),
                    {},
                    expected_status=403,
                    check_payload=False,
                )

    def test_delete_role_authorized(self):
        self.token = self.create_user_with_role(ADMIN_ROLE)
        response = self.client.delete(
            self.url + str(VIEWER_ROLE) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(501, response.status_code)

    def test_delete_role_not_authorized(self):
        response = self.client.delete(
            self.url + str(VIEWER_ROLE) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(403, response.status_code)


class TestUserRolesListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = USER_ROLE_URL
        self.model = UserRoleModel
        self.roles_with_access = UserRoleListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {
                "id": 1,
                "role": "planner",
                "role_id": 2,
                "user": "testname",
                "user_id": 1,
            },
            {
                "id": 2,
                "role": "planner",
                "role_id": 2,
                "user": "testuser3",
                "user_id": 2,
            },
            {"id": 3, "role": "admin", "role_id": 3, "user": "testuser3", "user_id": 2},
        ]
        self.new_user_role = {"user_id": 1, "role_id": 3}

    def tearDown(self):
        super().tearDown()

    def test_get_user_roles_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(self.payload, response.json)

    def test_get_user_roles_not_authorized_user(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )
                self.assertEqual(403, response.status_code)

    def test_post_role_assignment_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            self.create_new_row(self.url, self.model, self.new_user_role)

    def test_post_role_assignment_not_authorized_user(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                self.create_new_row(
                    self.url, self.model, {}, expected_status=403, check_payload=False
                )


class TestUserRolesDetailEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = USER_ROLE_URL
        self.model = UserRoleModel
        self.roles_with_access = UserRoleDetailEndpoint.ROLES_WITH_ACCESS
        self.payload = {
            "id": 1,
            "role": "planner",
            "role_id": 2,
            "user": "testname",
            "user_id": 1,
        }

    def tearDown(self):
        super().tearDown()

    def test_get_user_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url + str(self.payload["id"]) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(self.payload, response.json)

    def test_get_user_role_not_authorized_user(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url + str(self.payload["id"]) + "/",
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )
                self.assertEqual(403, response.status_code)

    def test_delete_user_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.delete(
                self.url + str(self.payload["id"]) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)

    def test_delete_user_role_not_authorized_user(self):
        for role in BASE_ROLES:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.delete(
                    self.url + str(self.payload["id"]) + "/",
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )
                self.assertEqual(403, response.status_code)
