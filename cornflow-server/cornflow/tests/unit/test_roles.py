"""
Unit test for the role endpoints
"""

import json
import logging as log

from cornflow.commands import access_init_command
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
    ViewModel,
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


class TestRegisterRolesCommand(CustomTestCase):
    def setUp(self):
        super().setUp()

    def test_register_roles_command_cornflow_only(self):
        """
        Test register_roles_command with Cornflow base roles only
        """
        from cornflow.commands.roles import register_roles_command

        # Clear existing roles for clean test
        existing_roles = RoleModel.get_all_objects().all()
        for role in existing_roles:
            role.delete()

        # Register only Cornflow base roles
        result = register_roles_command(external_app=None, verbose=False)

        self.assertTrue(result)

        # Check that all ROLES_MAP roles are created
        roles_in_db = RoleModel.get_all_objects().all()
        role_names = [role.name for role in roles_in_db]
        expected_names = list(ROLES_MAP.values())

        self.assertEqual(len(roles_in_db), len(ROLES_MAP))
        self.assertCountEqual(role_names, expected_names)

    def test_register_roles_command_with_custom_roles(self):
        """
        Test register_roles_command with custom roles from ROLES_WITH_ACCESS
        """
        from cornflow.commands.roles import register_roles_command
        from unittest.mock import Mock, patch

        # Clear existing roles for clean test
        existing_roles = RoleModel.get_all_objects().all()
        for role in existing_roles:
            role.delete()

        # Mock external app structure
        mock_endpoint_1 = Mock()
        mock_endpoint_1.ROLES_WITH_ACCESS = [1, 2, 888]  # 888 is custom

        mock_endpoint_2 = Mock()
        mock_endpoint_2.ROLES_WITH_ACCESS = [2, 3, 999]  # 999 is custom

        mock_endpoint_3 = Mock()
        mock_endpoint_3.ROLES_WITH_ACCESS = [888, 1000]  # 888 duplicate, 1000 new

        mock_resources = [
            {"resource": mock_endpoint_1, "endpoint": "test_endpoint_1"},
            {"resource": mock_endpoint_2, "endpoint": "test_endpoint_2"},
            {"resource": mock_endpoint_3, "endpoint": "test_endpoint_3"},
        ]

        mock_external_module = Mock()
        mock_external_module.endpoints.resources = mock_resources

        # Mock import_module to return our mock module
        with patch("cornflow.commands.roles.import_module") as mock_import:
            mock_import.return_value = mock_external_module

            # Register roles with external app
            result = register_roles_command(
                external_app="test_external_app", verbose=True
            )

        self.assertTrue(result)

        # Check that all roles are created
        roles_in_db = RoleModel.get_all_objects().all()
        role_ids = [role.id for role in roles_in_db]
        role_names = [role.name for role in roles_in_db]

        # Should have base roles + custom roles
        expected_base_ids = list(ROLES_MAP.keys())
        expected_custom_ids = [888, 999, 1000]
        expected_all_ids = expected_base_ids + expected_custom_ids

        self.assertEqual(len(roles_in_db), len(expected_all_ids))
        self.assertCountEqual(role_ids, expected_all_ids)

        # Check that custom roles have auto-generated names
        for role in roles_in_db:
            if role.id in expected_custom_ids:
                expected_name = f"custom_role_{role.id}"
                self.assertEqual(role.name, expected_name)
            else:
                # Base roles should have their original names
                self.assertEqual(role.name, ROLES_MAP[role.id])

    def test_register_roles_command_no_duplicates(self):
        """
        Test that register_roles_command doesn't create duplicate roles
        """
        from cornflow.commands.roles import register_roles_command
        from unittest.mock import Mock, patch

        # Clear existing roles for clean test
        existing_roles = RoleModel.get_all_objects().all()
        for role in existing_roles:
            role.delete()

        # First run - register base roles
        register_roles_command(external_app=None, verbose=False)

        initial_count = len(RoleModel.get_all_objects().all())

        # Mock external app with custom role
        mock_endpoint = Mock()
        mock_endpoint.ROLES_WITH_ACCESS = [1, 2, 888]  # 1,2 already exist, 888 is new

        mock_resources = [
            {"resource": mock_endpoint, "endpoint": "test_endpoint"},
        ]

        mock_external_module = Mock()
        mock_external_module.endpoints.resources = mock_resources

        with patch("cornflow.commands.roles.import_module") as mock_import:
            mock_import.return_value = mock_external_module

            # Second run - should only add new custom role
            result = register_roles_command(
                external_app="test_external_app", verbose=False
            )

        self.assertTrue(result)

        final_count = len(RoleModel.get_all_objects().all())

        # Should have added only 1 new role (888)
        self.assertEqual(final_count, initial_count + 1)

        # Check that custom role was created correctly
        custom_role = RoleModel.query.filter_by(id=888).first()
        self.assertIsNotNone(custom_role)
        self.assertEqual(custom_role.name, "custom_role_888")

    def test_register_roles_command_external_app_error_handling(self):
        """
        Test error handling when external app cannot be loaded
        """
        from cornflow.commands.roles import register_roles_command
        from unittest.mock import patch

        # Mock import_module to raise an exception
        with patch("cornflow.commands.roles.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            # Should handle the error gracefully
            result = register_roles_command(
                external_app="nonexistent_app", verbose=True
            )

        self.assertTrue(result)

        # Should still have base roles even if external app fails
        roles_in_db = RoleModel.get_all_objects().all()
        self.assertEqual(len(roles_in_db), len(ROLES_MAP))

    def test_custom_role_name_generation(self):
        """
        Test that custom role names are generated correctly in RoleModel
        """
        # Test role with only ID (should generate name)
        role_data = {"id": 999}
        role = RoleModel(role_data)

        self.assertEqual(role.id, 999)
        self.assertEqual(role.name, "custom_role_999")

        # Test role with both ID and name (should use provided name)
        role_data_with_name = {"id": 888, "name": "Production Manager"}
        role_with_name = RoleModel(role_data_with_name)

        self.assertEqual(role_with_name.id, 888)
        self.assertEqual(role_with_name.name, "Production Manager")

        # Test role with name but no ID (should use provided name)
        role_data_name_only = {"name": "Custom Role"}
        role_name_only = RoleModel(role_data_name_only)

        self.assertIsNone(role_name_only.id)
        self.assertEqual(role_name_only.name, "Custom Role")

    def test_complete_role_lifecycle_integration(self):
        """
        Test completo del ciclo de vida de roles custom y permisos durante despliegues
        Simula: crear rol -> endpoint inicial -> añadir rol -> redespliegue -> quitar rol -> redespliegue
        """
        from cornflow.commands.roles import register_roles_command
        from cornflow.commands.permissions import register_base_permissions_command
        from cornflow.models import PermissionViewRoleModel, ViewModel
        from cornflow.shared.const import PLANNER_ROLE, SERVICE_ROLE
        from cornflow.shared.const import (
            GET_ACTION,
            PATCH_ACTION,
            POST_ACTION,
            PUT_ACTION,
            DELETE_ACTION,
        )
        from unittest.mock import Mock, patch

        # === PASO 1: Crear un rol nuevo en la BBDD ===
        # En el caso real sería el propio usuario el que lo guardaría en la bbdd
        custom_role_id = 888
        custom_role = RoleModel({"id": custom_role_id, "name": "Production Manager"})
        custom_role.save()

        # Verificar que el rol se creó
        created_role = RoleModel.query.filter_by(id=custom_role_id).first()
        self.assertIsNotNone(created_role)
        self.assertEqual(created_role.name, "Production Manager")

        # === PASO 2: Crear endpoint con ROLES_WITH_ACCESS [PLANNER, SERVICE] ===
        mock_endpoint = Mock()
        mock_endpoint.ROLES_WITH_ACCESS = [PLANNER_ROLE, SERVICE_ROLE]

        mock_resources = [
            {"resource": mock_endpoint, "endpoint": "test_production_endpoint"},
        ]

        # Registrar la vista primero
        test_view = ViewModel(
            {
                "name": "test_production_endpoint",
                "url_rule": "/test-production/",
                "description": "Test production endpoint for role testing",
            }
        )
        test_view.save()

        mock_external_module = Mock()
        mock_external_module.endpoints.resources = mock_resources
        # "redesplegamos de mentira"
        access_init_command(verbose=True)

        # === PASO 3: Comprobar que no hay ningún endpoint que use el rol custom ===
        permissions_before = PermissionViewRoleModel.query.filter_by(
            role_id=custom_role_id, api_view_id=test_view.id
        ).all()
        self.assertEqual(len(permissions_before), 0)

        # === PASO 4: Simular despliegue inicial y comprobar permisos ===
        with patch("cornflow.commands.permissions.import_module") as mock_import_perms:
            mock_import_perms.return_value = mock_external_module
            register_base_permissions_command(external_app="test_app", verbose=False)

        # Verificar que se crearon permisos para PLANNER y SERVICE, pero NO para custom_role
        expected_actions = [
            GET_ACTION,
            PATCH_ACTION,
            POST_ACTION,
            PUT_ACTION,
            DELETE_ACTION,
        ]

        for role_id in [PLANNER_ROLE, SERVICE_ROLE]:
            for action in expected_actions:
                perm = PermissionViewRoleModel.query.filter_by(
                    role_id=role_id, action_id=action, api_view_id=test_view.id
                ).first()
                self.assertIsNotNone(
                    perm,
                    f"Debería existir permiso para role {role_id}, action {action}",
                )

        # Verificar que NO hay permisos para el rol custom
        custom_perms = PermissionViewRoleModel.query.filter_by(
            role_id=custom_role_id, api_view_id=test_view.id
        ).all()
        self.assertEqual(
            len(custom_perms), 0, "No debería haber permisos para el rol custom aún"
        )

        # === PASO 5: Añadir rol custom a ROLES_WITH_ACCESS ===
        mock_endpoint.ROLES_WITH_ACCESS = [PLANNER_ROLE, SERVICE_ROLE, custom_role_id]

        # === PASO 6: Fingir redespliegue ===
        with patch("cornflow.commands.permissions.import_module") as mock_import_perms:
            mock_import_perms.return_value = mock_external_module
            register_base_permissions_command(external_app="test_app", verbose=False)

        # === PASO 7: Comprobar que el rol nuevo sigue en la tabla de roles ===
        role_after_redeploy = RoleModel.query.filter_by(id=custom_role_id).first()
        self.assertIsNotNone(role_after_redeploy)
        self.assertEqual(role_after_redeploy.name, "Production Manager")

        # === PASO 8: Comprobar que existen los permisos para el rol nuevo ===
        for action in expected_actions:
            perm = PermissionViewRoleModel.query.filter_by(
                role_id=custom_role_id, action_id=action, api_view_id=test_view.id
            ).first()
            self.assertIsNotNone(
                perm, f"Debería existir permiso para custom role, action {action}"
            )

        # Contar permisos totales para el rol custom
        total_custom_perms = PermissionViewRoleModel.query.filter_by(
            role_id=custom_role_id, api_view_id=test_view.id
        ).count()
        self.assertEqual(total_custom_perms, len(expected_actions))

        # === PASO 9: Cambiar ROLES_WITH_ACCESS para quitar PLANNER ===
        mock_endpoint.ROLES_WITH_ACCESS = [
            SERVICE_ROLE,
            custom_role_id,
        ]  # Quitamos PLANNER

        # === PASO 10: Fingir redespliegue ===
        with patch("cornflow.commands.permissions.import_module") as mock_import_perms:
            mock_import_perms.return_value = mock_external_module
            register_base_permissions_command(external_app="test_app", verbose=False)

        # === PASO 11: Comprobar que se eliminaron los permisos de PLANNER ===
        # Los permisos de PLANNER deberían haber sido eliminados
        planner_perms_after = PermissionViewRoleModel.query.filter_by(
            role_id=PLANNER_ROLE, api_view_id=test_view.id
        ).all()
        self.assertEqual(
            len(planner_perms_after),
            0,
            "Los permisos de PLANNER deberían haber sido eliminados",
        )

        # Los permisos de SERVICE y custom_role deberían seguir existiendo
        for role_id in [SERVICE_ROLE, custom_role_id]:
            role_perms = PermissionViewRoleModel.query.filter_by(
                role_id=role_id, api_view_id=test_view.id
            ).count()
            self.assertEqual(
                role_perms,
                len(expected_actions),
                f"Los permisos de role {role_id} deberían seguir existiendo",
            )

        # === CLEANUP ===
        # Limpiar permisos restantes
        remaining_perms = PermissionViewRoleModel.query.filter_by(
            api_view_id=test_view.id
        ).all()
        for perm in remaining_perms:
            perm.delete()

        # Limpiar rol custom
        custom_role.delete()

        # Limpiar vista
        test_view.delete()
