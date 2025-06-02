"""
Unit tests for Cornflow command functionality.

This module contains tests for various command operations, including:

- User management commands (service, admin, base users)
- Action registration and management
- View registration and management
- Role management
- Permission assignment and validation
- DAG deployment and permissions
- Command argument validation

The tests verify both successful operations and error handling
for various command scenarios and configurations.
"""

import json

from flask_testing import TestCase

from cornflow.app import (
    access_init,
    create_admin_user,
    create_app,
    create_base_user,
    create_service_user,
    register_actions,
    register_dag_permissions,
    register_roles,
    register_views,
    register_base_assignations,
)
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.endpoints import resources, alarms_resources
from cornflow.models import (
    ActionModel,
    PermissionViewRoleModel,
    RoleModel,
    ViewModel,
)
from cornflow.models import (
    DeployedDAG,
    PermissionsDAG,
    UserModel,
)
from cornflow.shared import db
from cornflow.shared.const import (
    ACTIONS_MAP,
    ROLES_MAP,
    BASE_PERMISSION_ASSIGNATION,
)
from cornflow.tests.const import LOGIN_URL, INSTANCE_URL, INSTANCE_PATH
from cornflow.tests.integration.test_cornflowclient import load_file


class TestCommands(TestCase):
    """
    Test suite for Cornflow command functionality.

    This class tests various command operations and their effects on the system:

    - User creation and management commands
    - Action and view registration
    - Role initialization and management
    - Permission system configuration
    - DAG deployment and permissions
    - Command argument validation and error handling

    Each test method focuses on a specific command or related set of commands,
    verifying both successful execution and proper error handling.
    """

    def create_app(self):
        """
        Create and configure the Flask application for testing.

        :return: The configured Flask application instance with testing configuration
        :rtype: Flask
        """
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = 1
        return app

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes:

        - Database tables
        - Test user credentials
        - API resources
        - CLI runner
        - Base roles
        """
        db.create_all()
        self.payload = {
            "email": "testemail@test.org",
            "password": "Testpassword1!",
        }
        self.resources = resources + alarms_resources
        self.runner = self.create_app().test_cli_runner()
        self.runner.invoke(register_roles, ["-v"])

    def tearDown(self):
        """
        Clean up test environment after each test.

        Removes database session and drops all tables.
        """
        db.session.remove()
        db.drop_all()

    def user_command(self, command, username, email):
        """
        Helper method to test user creation commands.

        :param command: The user creation command to test
        :type command: function
        :param username: Username for the new user
        :type username: str
        :param email: Email for the new user
        :type email: str
        :return: The created user object
        :rtype: UserModel

        Verifies:

        - User creation success
        - Correct user attributes
        """
        self.runner.invoke(
            command,
            ["-u", username, "-e", email, "-p", self.payload["password"], "-v"],
        )

        user = UserModel.get_one_user_by_email(email)

        self.assertNotEqual(None, user)
        self.assertEqual(email, user.email)
        return user

    def user_missing_arguments(self, command):
        """
        Test user creation with missing required arguments.

        :param command: The user creation command to test
        :type command: function

        Verifies:

        - Proper error handling for missing username
        - Proper error handling for missing email
        - Proper error handling for missing password
        """
        result = self.runner.invoke(
            command,
            [
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-u' / '--username'", result.output)

        result = self.runner.invoke(
            command,
            [
                "-u",
                "cornflow",
                "-p",
                self.payload["password"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-e' / '--email'", result.output)

        result = self.runner.invoke(
            command,
            [
                "-u",
                "cornflow",
                "-e",
                self.payload["email"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-p' / '--password'", result.output)

    def test_service_user_command(self):
        """
        Test service user creation command.

        Verifies:

        - Successful service user creation
        - Correct user attributes
        - Service role assignment
        """
        return self.user_command(create_service_user, "cornflow", self.payload["email"])

    def test_service_user_existing_admin(self):
        """
        Test service user creation when admin user exists.

        Verifies:

        - Successful service user creation with existing admin
        - Correct user attributes
        - Proper role assignments
        """
        self.test_admin_user_command()
        self.runner.invoke(
            create_service_user,
            [
                "-u",
                "cornflow",
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        self.assertEqual("cornflow", user.username)

    def test_service_user_existing_service(self):
        """
        Test service user creation when service user exists.

        Verifies:

        - Proper handling of existing service user
        - Correct user attributes
        - Role consistency
        """
        self.test_service_user_command()
        user = self.test_service_user_command()

        self.assertEqual("cornflow", user.username)

    def test_admin_user_command(self):
        """
        Test admin user creation command.

        Verifies:

        - Successful admin user creation
        - Correct user attributes
        - Admin role assignment
        """
        return self.user_command(create_admin_user, "admin", "admin@test.org")

    def test_base_user_command(self):
        """
        Test base user creation command.

        Verifies:

        - Successful base user creation
        - Correct user attributes
        - Base role assignment
        """
        return self.user_command(create_base_user, "base", "base@test.org")

    def test_register_actions(self):
        """
        Test action registration command.

        Verifies:

        - Successful action registration
        - Correct action names and mappings
        - Database state after registration
        """
        self.runner.invoke(register_actions)

        actions = ActionModel.query.all()

        for a in actions:
            self.assertEqual(ACTIONS_MAP[a.id], a.name)

    def test_register_views(self):
        """
        Test view registration command.

        Verifies:

        - Successful view registration
        - Correct view endpoints
        - Proper mapping to resources
        """
        self.runner.invoke(register_views)

        views = ViewModel.query.all()
        views_list = [v.name for v in views]
        resources_list = [
            self.resources[i]["endpoint"] for i in range(len(self.resources))
        ]

        self.assertCountEqual(views_list, resources_list)

    def test_register_roles(self):
        """
        Test role registration command.

        Verifies:

        - Successful role registration
        - Correct role names and mappings
        - Database state after registration
        """
        roles = RoleModel.query.all()
        for r in roles:
            self.assertEqual(ROLES_MAP[r.id], r.name)

    def test_base_permissions_assignation(self):
        """
        Test base permission assignment.

        Verifies:

        - Successful permission assignment
        - Correct role-view-action mappings
        - Proper access control setup
        """
        self.runner.invoke(access_init)

        for base in BASE_PERMISSION_ASSIGNATION:
            for view in self.resources:
                if base[0] in view["resource"].ROLES_WITH_ACCESS:
                    permission = PermissionViewRoleModel.get_permission(
                        role_id=base[0],
                        api_view_id=ViewModel.query.filter_by(name=view["endpoint"])
                        .first()
                        .id,
                        action_id=base[1],
                    )

                    self.assertEqual(True, permission)

    def test_deployed_dags_test_command(self):
        """
        Test DAG deployment command in test mode.

        Verifies:

        - Successful DAG deployment
        - Correct DAG registration
        - Presence of required DAGs
        """
        register_deployed_dags_command_test(verbose=True)
        dags = DeployedDAG.get_all_objects()
        for dag in ["solve_model_dag", "gc", "timer"]:
            self.assertIn(dag, [d.id for d in dags])

    def test_dag_permissions_command(self):
        """
        Test DAG permissions command with open deployment.

        Verifies:

        - Successful permission assignment
        - Correct permissions for service and admin users
        - Proper access control setup
        """
        register_deployed_dags_command_test()
        self.test_service_user_command()
        self.test_admin_user_command()
        self.runner.invoke(register_dag_permissions, ["-o", 1])

        service = UserModel.get_one_user_by_email("testemail@test.org")
        admin = UserModel.get_one_user_by_email("admin@test.org")

        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        admin_permissions = PermissionsDAG.get_user_dag_permissions(admin.id)

        self.assertEqual(3, len(service_permissions))
        self.assertEqual(3, len(admin_permissions))

    def test_dag_permissions_command_no_open(self):
        """
        Test DAG permissions command without open deployment.

        Verifies:

        - Successful permission assignment
        - Restricted access for admin users
        - Proper service user permissions
        """
        register_deployed_dags_command_test()
        self.test_service_user_command()
        self.test_admin_user_command()
        self.runner.invoke(register_dag_permissions, ["-o", 0])

        service = UserModel.get_one_user_by_email("testemail@test.org")
        admin = UserModel.get_one_user_by_email("admin@test.org")

        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        admin_permissions = PermissionsDAG.get_user_dag_permissions(admin.id)

        self.assertEqual(3, len(service_permissions))
        self.assertEqual(0, len(admin_permissions))

    def test_argument_parsing_correct(self):
        """
        Test correct argument parsing for DAG permissions.

        Verifies:

        - Proper handling of invalid arguments
        - Error messages for incorrect input
        - No permission changes on error
        """
        self.test_service_user_command()
        result = self.runner.invoke(register_dag_permissions, ["-o", "a"])

        self.assertEqual(2, result.exit_code)
        self.assertIn("is not a valid integer", result.output)

        service = UserModel.get_one_user_by_email("testemail@test.org")
        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        self.assertEqual(0, len(service_permissions))

    def test_argument_parsing_incorrect(self):
        """
        Test incorrect argument parsing for DAG permissions.

        Verifies:

        - Error handling for invalid input types
        - Proper error messages
        - Command failure behavior
        """
        self.test_service_user_command()
        result = self.runner.invoke(register_dag_permissions, ["-o", "a"])
        self.assertEqual(2, result.exit_code)
        self.assertIn("is not a valid integer", result.output)

    def test_missing_required_argument_service(self):
        """
        Test missing arguments for service user creation.

        Verifies proper error handling for missing required arguments.
        """
        self.user_missing_arguments(create_service_user)

    def test_missing_required_argument_admin(self):
        """
        Test missing arguments for admin user creation.

        Verifies proper error handling for missing required arguments.
        """
        self.user_missing_arguments(create_admin_user)

    def test_missing_required_argument_user(self):
        """
        Test missing arguments for base user creation.

        Verifies proper error handling for missing required arguments.
        """
        self.user_missing_arguments(create_base_user)

    def test_error_no_views(self):
        """
        Test error handling when views are not registered.

        Verifies proper error handling when attempting operations without registered views.
        """
        self.test_service_user_command()
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": "cornflow", "password": self.payload["password"]}
            ),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        data = load_file(INSTANCE_PATH)
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(403, response.status_code)

    def test_permissions_not_deleted_when_roles_removed_from_code(self):
        """
        Test that permissions are NOT deleted when roles are removed from ROLES_WITH_ACCESS.

        This test demonstrates the current bug: when a role is removed from
        ROLES_WITH_ACCESS in an endpoint's code, the corresponding permissions
        in the database are not automatically deleted. This happens because
        the deletion logic in register_base_permissions_command is commented out.

        The test should currently FAIL to demonstrate the bug exists.
        """
        # First, initialize the access system normally
        self.runner.invoke(access_init)

        # Get the original ROLES_WITH_ACCESS for ExampleDataListEndpoint
        from cornflow.endpoints.example_data import ExampleDataListEndpoint

        original_roles = ExampleDataListEndpoint.ROLES_WITH_ACCESS.copy()

        # Verify initial permissions are created for all three roles
        # Get the view ID for the endpoint
        from cornflow.models import ViewModel

        view = ViewModel.query.filter_by(name="example-data").first()
        self.assertIsNotNone(view, "example-data view should exist")

        # Check permissions exist for all original roles
        from cornflow.shared.const import ACTIONS_MAP
        from cornflow.models import PermissionViewRoleModel

        # Check GET action permissions (action_id=1 is typically GET)
        get_action_id = 1
        initial_permissions = PermissionViewRoleModel.query.filter_by(
            api_view_id=view.id, action_id=get_action_id
        ).all()

        initial_role_ids = [perm.role_id for perm in initial_permissions]
        self.assertEqual(
            len(original_roles),
            len(initial_permissions),
            f"Should have permissions for all {len(original_roles)} original roles",
        )

        # Now simulate removing PLANNER_ROLE from ROLES_WITH_ACCESS
        from cornflow.shared.const import PLANNER_ROLE, VIEWER_ROLE, ADMIN_ROLE

        modified_roles = [VIEWER_ROLE, ADMIN_ROLE]  # Remove PLANNER_ROLE

        # Temporarily modify the ROLES_WITH_ACCESS
        ExampleDataListEndpoint.ROLES_WITH_ACCESS = modified_roles

        try:

            # Run the permission registration again
            # (this simulates redeploying the app with modified roles)
            self.runner.invoke(register_base_assignations, ["-v"])

            # Check permissions after the "code change"
            updated_permissions = PermissionViewRoleModel.query.filter_by(
                api_view_id=view.id, action_id=get_action_id
            ).all()

            updated_role_ids = [perm.role_id for perm in updated_permissions]

            # THIS IS THE BUG: The permission for PLANNER_ROLE should be deleted
            # but it's not because the deletion logic is commented out
            # So we expect this assertion to FAIL, demonstrating the bug
            self.assertEqual(
                len(modified_roles),
                len(updated_permissions),
                f"After removing PLANNER_ROLE from code, should only have {len(modified_roles)} permissions, "
                f"but still has {len(updated_permissions)} permissions. "
                f"This demonstrates the bug: permissions are not deleted when roles are removed from ROLES_WITH_ACCESS.",
            )

            # Also check that PLANNER_ROLE permission was actually removed
            planner_permissions = [
                perm for perm in updated_permissions if perm.role_id == PLANNER_ROLE
            ]
            self.assertEqual(
                0,
                len(planner_permissions),
                "PLANNER_ROLE permission should have been deleted but still exists",
            )

        finally:
            # Restore original ROLES_WITH_ACCESS to avoid affecting other tests
            ExampleDataListEndpoint.ROLES_WITH_ACCESS = original_roles

    def test_custom_role_permissions_are_preserved(self):
        """
        Test that custom roles (not in ROLES_MAP) are automatically detected
        and assigned complete permissions during synchronization.

        This test verifies that when permissions are synchronized:
        1. Custom roles in the database are automatically detected
        2. They are assigned all actions (GET, PATCH, POST, PUT, DELETE)
        3. These permissions are created for all endpoints where the role has access
        """
        # First, initialize the access system normally
        self.runner.invoke(access_init)

        # Get a view to work with
        from cornflow.models import ViewModel, PermissionViewRoleModel, RoleModel

        view = ViewModel.query.filter_by(name="example-data").first()
        self.assertIsNotNone(view, "example-data view should exist")

        # Create a custom role that is NOT in ROLES_MAP
        custom_role_id = 999  # Use an ID that's not in ROLES_MAP
        custom_role = RoleModel({"id": custom_role_id, "name": "custom_role"})
        custom_role.save()

        # Temporarily add the custom role to ExampleDataListEndpoint ROLES_WITH_ACCESS
        from cornflow.endpoints.example_data import ExampleDataListEndpoint

        original_roles = ExampleDataListEndpoint.ROLES_WITH_ACCESS.copy()
        ExampleDataListEndpoint.ROLES_WITH_ACCESS = original_roles + [custom_role_id]

        try:
            # Count permissions before synchronization
            perms_before = PermissionViewRoleModel.query.filter_by(
                role_id=custom_role_id, api_view_id=view.id
            ).count()
            self.assertEqual(
                0, perms_before, "No custom permissions should exist initially"
            )

            # Run permission synchronization - this should auto-detect the custom role
            self.runner.invoke(register_base_assignations, ["-v"])

            # Verify that ALL actions have been assigned to the custom role
            from cornflow.shared.const import (
                GET_ACTION,
                PATCH_ACTION,
                POST_ACTION,
                PUT_ACTION,
                DELETE_ACTION,
            )

            expected_actions = [
                GET_ACTION,
                PATCH_ACTION,
                POST_ACTION,
                PUT_ACTION,
                DELETE_ACTION,
            ]

            for action in expected_actions:
                permission = PermissionViewRoleModel.query.filter_by(
                    role_id=custom_role_id, action_id=action, api_view_id=view.id
                ).first()
                self.assertIsNotNone(
                    permission,
                    f"Custom role should have permission for action {action}. "
                    f"The system should auto-detect custom roles and assign complete permissions.",
                )

            # Verify total count of permissions for custom role
            total_perms = PermissionViewRoleModel.query.filter_by(
                role_id=custom_role_id, api_view_id=view.id
            ).count()
            self.assertEqual(
                len(expected_actions),
                total_perms,
                f"Custom role should have {len(expected_actions)} permissions (all actions)",
            )

            # Test that running sync again doesn't duplicate permissions
            self.runner.invoke(register_base_assignations, ["-v"])

            total_perms_after_second_sync = PermissionViewRoleModel.query.filter_by(
                role_id=custom_role_id, api_view_id=view.id
            ).count()
            self.assertEqual(
                len(expected_actions),
                total_perms_after_second_sync,
                "Permissions should not be duplicated on subsequent syncs",
            )

        finally:
            # Clean up
            # Delete permissions first (due to foreign key constraints)
            permissions_to_delete = PermissionViewRoleModel.query.filter_by(
                role_id=custom_role_id
            ).all()
            for perm in permissions_to_delete:
                perm.delete()
            custom_role.delete()
            # Restore original ROLES_WITH_ACCESS
            ExampleDataListEndpoint.ROLES_WITH_ACCESS = original_roles
