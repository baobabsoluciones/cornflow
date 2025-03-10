"""
Unit test for the role endpoints
"""

import json
import logging as log
from cornflow.models import PermissionViewRoleModel, RoleModel

# Import from internal modules
from cornflow.endpoints import (
    RoleDetailEndpoint,
    RolesListEndpoint,
    UserRoleListEndpoint,
    UserRoleDetailEndpoint,
)
from cornflow.models import (
    UserModel,
    UserRoleModel,
)
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    ROLES_MAP,
    VIEWER_ROLE,
)
from cornflow.tests.const import ROLES_URL, USER_ROLE_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestRolesListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.payload = {"name": "new_role"}
        self.payloads = [{"id": key, "name": value} for key, value in ROLES_MAP.items()]
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
                    "Authorization": f"Bearer {self.token}",
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertCountEqual(self.payloads, response.json)

    def test_post_new_role(self):
        role = self.roles_with_access[0]
        self.token = self.create_user_with_role(role)
        payload = {"name": "test_role_3"}
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual("test_role_3", response.json["name"])

        response = self.client.get(
            self.url,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(5, len(response.json))

    def test_get_no_roles(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )
                self.assertEqual(403, response.status_code)

    def test_new_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            self.payload["name"] += str(role)
            self.create_new_row(self.url, self.model, self.payload)

    def test_new_role_not_authorized(self):
        for role in ROLES_MAP:
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
        for role in ROLES_MAP:
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
                    "Authorization": f"Bearer {self.token}",
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
        for role in ROLES_MAP:
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
                "Authorization": f"Bearer {self.token}",
            },
        )

        self.assertEqual(501, response.status_code)

    def test_delete_role_not_authorized(self):
        response = self.client.delete(
            self.url + str(VIEWER_ROLE) + "/",
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
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
                    "Authorization": f"Bearer {self.token}",
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(self.payload, response.json)

    def test_get_user_roles_not_authorized_user(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )
                self.assertEqual(403, response.status_code)

    def test_post_role_assignment_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            self.create_new_row(self.url, self.model, self.new_user_role)

    def test_post_role_assignment_not_authorized_user(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                self.create_new_row(
                    self.url, self.model, {}, expected_status=403, check_payload=False
                )

    def test_post_already_assigned_role(self):
        role = self.roles_with_access[0]
        self.token = self.create_user_with_role(role)
        self.create_new_row(self.url, self.model, self.new_user_role)
        self.create_new_row(
            self.url,
            self.model,
            self.new_user_role,
            expected_status=400,
            check_payload=False,
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

        self.payload_2 = {
            "id": 4,
            "role": "planner",
            "role_id": 2,
            "user": "testuser3",
            "user_id": 2,
        }
        log.info("super set up done")

    def tearDown(self):
        super().tearDown()

    def test_get_user_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url
                + str(self.payload["user_id"])
                + "/"
                + str(self.payload["role_id"])
                + "/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(self.payload, response.json)

    def test_get_user_role_not_authorized_user(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    self.url
                    + str(self.payload["user_id"])
                    + "/"
                    + str(self.payload["role_id"])
                    + "/",
                    follow_redirects=True,
                    headers=self.get_header_with_auth(self.token),
                )
                self.assertEqual(403, response.status_code)

    def test_delete_user_role_authorized_user(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.delete(
                self.url
                + str(self.payload["user_id"])
                + "/"
                + str(self.payload["role_id"])
                + "/",
                follow_redirects=True,
                headers=self.get_header_with_auth(self.token),
            )
            self.assertEqual(200, response.status_code)

    def test_delete_and_create_user_role_authorized_user(self):
        role = self.roles_with_access[0]
        data = {
            "username": "testuser" + str(role),
            "email": "testemail" + str(role) + "@test.org",
            "password": "Testpassword1!",
        }
        user_response = self.create_user(data)

        self.assign_role(user_response.json["id"], role)

        self.client.delete(
            self.url + str(user_response.json["id"]) + "/" + str(PLANNER_ROLE) + "/",
            follow_redirects=True,
            headers=self.get_header_with_auth(user_response.json["token"]),
        )

        role_response = self.create_role_endpoint(
            user_response.json["id"], PLANNER_ROLE, user_response.json["token"]
        )

        self.assertEqual(201, user_response.status_code)
        self.assertEqual(201, role_response.status_code)
        self.assertEqual(self.payload_2, role_response.json)

    def test_delete_user_role_not_authorized_user(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.delete(
                    self.url
                    + str(self.payload["user_id"])
                    + "/"
                    + str(self.payload["role_id"])
                    + "/",
                    follow_redirects=True,
                    headers=self.get_header_with_auth(self.token),
                )
                self.assertEqual(403, response.status_code)

    def test_delete_all_user_roles(self):
        # create some user:
        data = {
            "username": "testuser",
            "email": "testemail" + "@test.org",
            "password": "Testpassword1!",
        }
        user_response = self.create_user(data)
        user_id = user_response.json["id"]
        # give it all roles:
        for role in ROLES_MAP:
            self.assign_role(user_id, role)
        all_roles = UserModel.get_one_user(user_id).roles
        diff = set(r for r in all_roles).symmetric_difference(ROLES_MAP.keys())
        self.assertEqual(len(all_roles), len(ROLES_MAP))
        self.assertEqual(len(diff), 0)
        UserRoleModel.del_one_user(user_id)
        all_roles = UserRoleModel.get_all_objects(user_id=user_id).all()
        self.assertEqual(all_roles, [])


class TestRolesModelMethods(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = ROLES_URL
        self.model = RoleModel
        self.payload = {"name": "test_role"}

    def test_user_role_delete_cascade(self):
        payload = {"user_id": self.user.id}
        self.token = self.create_user_with_role(ADMIN_ROLE)
        self.cascade_delete(
            self.url,
            self.model,
            self.payload,
            USER_ROLE_URL,
            UserRoleModel,
            payload,
            "role_id",
        )

    def test_permission_delete_cascade(self):
        self.token = self.create_user_with_role(ADMIN_ROLE)
        idx = self.create_new_row(self.url, self.model, self.payload)
        payload = {"action_id": 1, "api_view_id": 1, "role_id": idx}
        PermissionViewRoleModel(payload).save()

        role = self.model.query.get(idx)
        permission = PermissionViewRoleModel.query.filter_by(role_id=idx).first()

        self.assertIsNotNone(role)
        self.assertIsNotNone(permission)

        role.delete()

        role = self.model.query.get(idx)
        permission = PermissionViewRoleModel.query.filter_by(role_id=idx).first()

        self.assertIsNone(role)
        self.assertIsNone(permission)

    def test_repr_method(self):
        self.token = self.create_user_with_role(ADMIN_ROLE)
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.repr_method(idx, "<Role test_role>")

    def test_str_method(self):
        self.token = self.create_user_with_role(ADMIN_ROLE)
        idx = self.create_new_row(self.url, self.model, self.payload)
        self.str_method(idx, "<Role test_role>")

    def test_get_all_objects(self):
        """
        Tests the get_all_objects method
        """
        # We expect 4 roles to be present (from ROLES_MAP constant)
        instances = RoleModel.get_all_objects().all()
        self.assertEqual(len(instances), 4)

        # Check that all the roles from ROLES_MAP are present
        role_names = [role.name for role in instances]
        expected_names = list(ROLES_MAP.values())
        self.assertCountEqual(role_names, expected_names)

        # Test offset parameter - should get all except the first role
        instances = RoleModel.get_all_objects(offset=1).all()
        self.assertEqual(len(instances), 3)

        # Get the names of all roles except the first one
        remaining_roles = [role.name for role in instances]
        # The first role is skipped due to offset=1
        first_role = RoleModel.get_all_objects().first().name
        self.assertNotIn(first_role, remaining_roles)

        # Test offset and limit parameters
        instances = RoleModel.get_all_objects(offset=1, limit=1).all()
        self.assertEqual(len(instances), 1)

        # Verify that we get the second role when using offset=1 and limit=1
        second_role = RoleModel.get_all_objects().all()[1]
        self.assertEqual(instances[0].id, second_role.id)
        self.assertEqual(instances[0].name, second_role.name)

        # Test filtering by name
        instances = RoleModel.get_all_objects(limit=1, name="admin").all()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].name, "admin")
