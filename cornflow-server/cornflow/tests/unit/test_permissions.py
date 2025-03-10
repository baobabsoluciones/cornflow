"""
Unit test for the permissions table
"""

# Import from libraries
import json

from cornflow.models import (
    ActionModel,
    PermissionViewRoleModel,
    RoleModel,
    ViewModel,
)

# Import from internal modules
from cornflow.app import create_app
from cornflow.endpoints import (
    PermissionsViewRoleEndpoint,
    PermissionsViewRoleDetailEndpoint,
)
from cornflow.models import InstanceModel
from cornflow.shared.const import GET_ACTION, ROLES_MAP, VIEWER_ROLE
from cornflow.tests.const import INSTANCE_PATH, INSTANCE_URL, PERMISSION_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestPermissionsViewRoleEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.model = PermissionViewRoleModel
        self.roles_with_access = PermissionsViewRoleEndpoint.ROLES_WITH_ACCESS
        self.payload = {"role_id": 1, "permission_id": 1, "api_view_id": 1}

    def tearDown(self):
        super().tearDown()

    def test_get_permissions_view_role(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)

            response = self.client.get(
                PERMISSION_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )

            self.assertEqual(200, response.status_code)

    def test_get_no_permissions_view_role(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    PERMISSION_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )

                self.assertEqual(403, response.status_code)

    def test_new_permission_authorized_user(self):
        api_view = 1
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            payload = {"role_id": 1, "action_id": 3, "api_view_id": api_view}
            self.create_new_row(PERMISSION_URL, self.model, payload)
            api_view += 1

    def test_new_role_not_authorized(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                self.create_new_row(
                    PERMISSION_URL,
                    self.model,
                    {},
                    expected_status=403,
                    check_payload=False,
                )


class TestPermissionViewRolesDetailEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.model = PermissionViewRoleModel
        self.roles_with_access = PermissionsViewRoleDetailEndpoint.ROLES_WITH_ACCESS
        self.payload = {"role_id": 1, "action_id": 3, "api_view_id": 1}
        self.items_to_check = []

    def test_modify_permission_authorized_user(self):
        authorized_user = self.roles_with_access[0]
        self.token = self.create_user_with_role(authorized_user)

        idx = self.client.post(
            PERMISSION_URL,
            follow_redirects=True,
            data=json.dumps(self.payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        ).json["id"]
        view_id = 2
        for role in self.roles_with_access:
            if role != self.roles_with_access[0]:
                self.token = self.create_user_with_role(role)
            updated_payload = {"action_id": 2, "api_view_id": view_id}
            self.update_row(
                PERMISSION_URL + str(idx) + "/",
                updated_payload,
                {"action_id": 2, "api_view_id": view_id, "id": idx},
            )
            view_id += 1

    def test_modify_permission_not_authorized(self):
        authorized_user = self.roles_with_access[0]
        self.token = self.create_user_with_role(authorized_user)
        idx = self.client.post(
            PERMISSION_URL,
            follow_redirects=True,
            data=json.dumps(self.payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        ).json["id"]
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                updated_payload = {"role_id": role, "action_id": 2}
                self.update_row(
                    PERMISSION_URL + str(idx) + "/",
                    updated_payload,
                    {},
                    expected_status=403,
                    check_payload=False,
                )

    def test_delete_permission_authorized(self):
        for authorized_user in self.roles_with_access:
            self.token = self.create_user_with_role(authorized_user)
            idx = self.client.post(
                PERMISSION_URL,
                follow_redirects=True,
                data=json.dumps(self.payload),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            ).json["id"]

            response = self.client.delete(
                PERMISSION_URL + str(idx) + "/",
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )
            self.assertEqual(200, response.status_code)

    def test_delete_permission_not_authorized(self):
        authorized_user = self.roles_with_access[0]
        self.token = self.create_user_with_role(authorized_user)
        idx = self.client.post(
            PERMISSION_URL,
            follow_redirects=True,
            data=json.dumps(self.payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        ).json["id"]

        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.delete(
                    PERMISSION_URL + str(idx) + "/",
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )
                self.assertEqual(403, response.status_code)


class TestPermissionsDagNoOpen(CustomTestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = 0
        return app

    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)

    def test_create_instance_no_permissions(self):
        self.create_new_row(self.url, self.model, self.payload, 403, False)

    def test_missing_schema(self):
        self.payload.pop("schema")
        self.create_new_row(self.url, self.model, self.payload, 400, False)


class TestPermissionsViewModel(CustomTestCase):
    def setUp(self):
        super().setUp()

    def test_permission_role_cascade_deletion(self):
        before_permissions = PermissionViewRoleModel.get_all_objects()
        role = RoleModel.get_one_object(VIEWER_ROLE)
        role.delete()
        after_permissions = PermissionViewRoleModel.get_all_objects()
        self.assertNotEqual(before_permissions, after_permissions)

    def test_permission_action_cascade_deletion(self):
        before_permissions = PermissionViewRoleModel.get_all_objects()
        action = ActionModel.get_one_object(GET_ACTION)
        action.delete()
        after_permissions = PermissionViewRoleModel.get_all_objects()
        self.assertNotEqual(before_permissions, after_permissions)

    def test_permission_api_view_cascade_deletion(self):
        before_permissions = PermissionViewRoleModel.get_all_objects()
        api_view = ViewModel.get_one_by_name("instance")
        api_view.delete()
        after_permissions = PermissionViewRoleModel.get_all_objects()
        self.assertNotEqual(before_permissions, after_permissions)
