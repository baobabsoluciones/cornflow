import unittest
import os
import json
from unittest.mock import patch, MagicMock
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.models import ViewModel
from cornflow.shared.const import (
    VIEWER_ROLE,
    PLANNER_ROLE,
    POST_ACTION,
    PATCH_ACTION,
    DELETE_ACTION,
)


class ExternalRoleCreationTestCase(CustomTestCase):
    """
    Test cases for external app custom role creation and removal functionality
    """

    def _load_expected_permissions(self, test_name):
        """Helper method to load expected permissions from JSON file"""
        test_data_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "expected_permissions.json"
        )
        with open(test_data_path, "r") as f:
            data = json.load(f)
        return [
            (role_id, action_id, endpoint_name)
            for role_id, action_id, endpoint_name in data[test_name]
        ]

    def _create_mock_external_app_resources(self):
        """Helper method to create mock external app resources"""
        # Create mock endpoint classes for external app
        mock_production_endpoint = MagicMock()
        mock_production_endpoint.ROLES_WITH_ACCESS = [
            888,
            PLANNER_ROLE,
        ]  # Custom role + standard role
        mock_production_endpoint.DESCRIPTION = "Production planning endpoint"

        mock_quality_endpoint = MagicMock()
        mock_quality_endpoint.ROLES_WITH_ACCESS = [
            777,
            VIEWER_ROLE,
        ]  # Custom role + standard role
        mock_quality_endpoint.DESCRIPTION = "Quality control endpoint"

        mock_scheduling_endpoint = MagicMock()
        mock_scheduling_endpoint.ROLES_WITH_ACCESS = [
            888,
            777,
            PLANNER_ROLE,
        ]  # Multiple custom roles
        mock_scheduling_endpoint.DESCRIPTION = "Scheduling optimizer endpoint"

        # Create mock resources structure for external app endpoints
        mock_resources = [
            {
                "endpoint": "production_planning",  # External app endpoint
                "urls": "/production-planning/",
                "resource": mock_production_endpoint,
            },
            {
                "endpoint": "quality_control",  # External app endpoint
                "urls": "/quality-control/",
                "resource": mock_quality_endpoint,
            },
            {
                "endpoint": "scheduling_optimizer",  # External app endpoint
                "urls": "/scheduling/",
                "resource": mock_scheduling_endpoint,
            },
        ]

        return mock_resources

    @patch("cornflow.commands.auxiliar.import_module")
    @patch("cornflow.commands.views.import_module")
    @patch("cornflow.commands.permissions.import_module")
    @patch.dict(
        os.environ, {"EXTERNAL_APP": "1", "EXTERNAL_APP_MODULE": "external_test_app"}
    )
    def test_custom_role_creation_removal(
        self, mock_import_views, mock_import_permissions, mock_import_auxiliar
    ):
        """
        Test that custom roles (like role 888) are properly created and removed
        when external app is configured with EXTRA_PERMISSION_ASSIGNATION
        """
        # Mock external app configuration
        mock_external_app = MagicMock()

        # Mock the shared.const module
        mock_shared = MagicMock()
        mock_const = MagicMock()
        mock_const.EXTRA_PERMISSION_ASSIGNATION = [
            (
                888,
                POST_ACTION,
                "production_planning",
            ),  # Custom endpoint from external app
            (777, PATCH_ACTION, "quality_control"),  # Custom endpoint from external app
            (VIEWER_ROLE, POST_ACTION, "scheduling_optimizer"),  # Extend standard role
            (PLANNER_ROLE, DELETE_ACTION, "quality_control"),  # Extend standard role
        ]
        mock_shared.const = mock_const
        mock_external_app.shared = mock_shared

        # Mock the endpoints.resources with fake external app endpoints
        mock_endpoints = MagicMock()
        mock_endpoints.resources = self._create_mock_external_app_resources()
        mock_external_app.endpoints = mock_endpoints

        mock_import_permissions.return_value = mock_external_app
        mock_import_views.return_value = mock_external_app
        mock_import_auxiliar.return_value = mock_external_app

        # Run the permissions registration
        from cornflow.commands.access import access_init_command

        # Mock the database session for testing
        with patch.object(db.session, "commit"):
            with patch.object(db.session, "rollback"):
                # Run the complete access initialization
                access_init_command(verbose=True)

                # Verify that custom permissions were created for the external roles
                from cornflow.models import PermissionViewRoleModel

                # Get all permissions for external app endpoints
                all_permissions = PermissionViewRoleModel.query.all()
                external_permissions = [
                    perm
                    for perm in all_permissions
                    if perm.api_view.name
                    in [
                        "production_planning",
                        "quality_control",
                        "scheduling_optimizer",
                    ]
                ]

                # Load expected permissions from JSON file
                expected_permissions = self._load_expected_permissions(
                    "test_custom_role_creation_removal"
                )

                # Verify each expected permission exists
                for role_id, action_id, endpoint_name in expected_permissions:
                    permission_exists = any(
                        p.role_id == role_id
                        and p.action_id == action_id
                        and p.api_view.name == endpoint_name
                        for p in external_permissions
                    )
                    self.assertTrue(
                        permission_exists,
                        f"Expected permission not found: role_id={role_id}, action_id={action_id}, endpoint={endpoint_name}",
                    )

                # Verify we don't have unexpected permissions
                actual_permission_tuples = {
                    (p.role_id, p.action_id, p.api_view.name)
                    for p in external_permissions
                }
                expected_permission_tuples = set(expected_permissions)

                unexpected_permissions = (
                    actual_permission_tuples - expected_permission_tuples
                )
                self.assertEqual(
                    len(unexpected_permissions),
                    0,
                    f"Found unexpected permissions: {unexpected_permissions}",
                )

                missing_permissions = (
                    expected_permission_tuples - actual_permission_tuples
                )
                self.assertEqual(
                    len(missing_permissions),
                    0,
                    f"Missing expected permissions: {missing_permissions}",
                )

    @patch("cornflow.commands.auxiliar.import_module")
    @patch("cornflow.commands.views.import_module")
    @patch("cornflow.commands.permissions.import_module")
    @patch.dict(
        os.environ, {"EXTERNAL_APP": "1", "EXTERNAL_APP_MODULE": "external_test_app"}
    )
    def test_role_removal_when_not_in_config(
        self, mock_import_permissions, mock_import_views, mock_import_auxiliar
    ):
        """
        Test that roles are properly removed when they're no longer in EXTRA_PERMISSION_ASSIGNATION
        """
        # First, create roles with permissions
        mock_external_app = MagicMock()

        # Mock the shared.const module
        mock_shared = MagicMock()
        mock_const = MagicMock()
        mock_const.EXTRA_PERMISSION_ASSIGNATION = [
            (10000, POST_ACTION, "production_planning"),
            (999, PATCH_ACTION, "quality_control"),
        ]
        mock_shared.const = mock_const
        mock_external_app.shared = mock_shared

        # Mock the endpoints.resources
        mock_endpoints = MagicMock()
        mock_endpoints.resources = self._create_mock_external_app_resources()
        mock_external_app.endpoints = mock_endpoints

        mock_import_permissions.return_value = mock_external_app
        mock_import_views.return_value = mock_external_app
        mock_import_auxiliar.return_value = mock_external_app

        # Create initial roles
        from cornflow.commands.access import access_init_command

        access_init_command(verbose=True)

        # Now update config to remove role 777
        mock_const.EXTRA_PERMISSION_ASSIGNATION = [
            (10000, POST_ACTION, "production_planning"),
        ]

        # Re-run permissions registration
        access_init_command(verbose=True)

        # Verify role 888 still has permissions but 777 does not
        from cornflow.models import PermissionViewRoleModel

        permissions_10000 = PermissionViewRoleModel.query.filter_by(role_id=10000).all()
        permissions_999 = PermissionViewRoleModel.query.filter_by(role_id=999).all()

        self.assertTrue(len(permissions_10000) > 0)
        self.assertEqual(len(permissions_999), 0)

    def test_fallback_when_no_external_config(self):
        """
        Test that the system falls back gracefully when EXTRA_PERMISSION_ASSIGNATION is not available
        """
        from cornflow.commands.access import access_init_command

        # Should not raise any exceptions
        try:
            access_init_command(verbose=True)
        except Exception as e:
            self.fail(f"access_init_command raised an exception: {e}")

    @patch("cornflow.commands.auxiliar.import_module")
    @patch("cornflow.commands.views.import_module")
    @patch("cornflow.commands.permissions.import_module")
    @patch.dict(
        os.environ, {"EXTERNAL_APP": "1", "EXTERNAL_APP_MODULE": "external_test_app"}
    )
    def test_external_app_missing_extra_permissions(
        self, mock_import_permissions, mock_import_views, mock_import_auxiliar
    ):
        """
        Test graceful handling when external app doesn't have EXTRA_PERMISSION_ASSIGNATION
        """
        # Mock external app without EXTRA_PERMISSION_ASSIGNATION
        mock_external_app = MagicMock()

        # Mock the shared module but without const.EXTRA_PERMISSION_ASSIGNATION
        mock_shared = MagicMock()
        mock_const = MagicMock()
        # Don't set EXTRA_PERMISSION_ASSIGNATION to trigger AttributeError
        del mock_const.EXTRA_PERMISSION_ASSIGNATION
        mock_shared.const = mock_const
        mock_external_app.shared = mock_shared

        # Mock the endpoints.resources
        mock_endpoints = MagicMock()
        mock_endpoints.resources = self._create_mock_external_app_resources()
        mock_external_app.endpoints = mock_endpoints

        mock_import_permissions.return_value = mock_external_app
        mock_import_views.return_value = mock_external_app
        mock_import_auxiliar.return_value = mock_external_app

        from cornflow.commands.access import access_init_command

        # Should not raise any exceptions, should fall back gracefully
        try:
            access_init_command(verbose=True)
        except Exception as e:
            self.fail(f"access_init_command raised an exception: {e}")

    @patch("cornflow.commands.auxiliar.import_module")
    @patch("cornflow.commands.views.import_module")
    @patch("cornflow.commands.permissions.import_module")
    @patch.dict(
        os.environ, {"EXTERNAL_APP": "1", "EXTERNAL_APP_MODULE": "external_test_app"}
    )
    def test_standard_role_extended_permissions(
        self, mock_import_permissions, mock_import_views, mock_import_auxiliar
    ):
        """
        Test that standard roles (like VIEWER_ROLE) can get extended permissions from external app
        """
        # Mock external app configuration with extended permissions for existing roles
        mock_external_app = MagicMock()

        # Mock the shared.const module
        mock_shared = MagicMock()
        mock_const = MagicMock()
        mock_const.EXTRA_PERMISSION_ASSIGNATION = [
            (VIEWER_ROLE, POST_ACTION, "production_planning"),  # Extend standard role
            (PLANNER_ROLE, DELETE_ACTION, "quality_control"),  # Extend standard role
        ]
        mock_shared.const = mock_const
        mock_external_app.shared = mock_shared

        # Mock the endpoints.resources
        mock_endpoints = MagicMock()
        mock_endpoints.resources = self._create_mock_external_app_resources()
        mock_external_app.endpoints = mock_endpoints

        mock_import_permissions.return_value = mock_external_app
        mock_import_views.return_value = mock_external_app
        mock_import_auxiliar.return_value = mock_external_app

        from cornflow.commands.access import access_init_command

        # Mock the database session for testing
        with patch.object(db.session, "commit"):
            with patch.object(db.session, "rollback"):
                # Run the complete access initialization
                access_init_command(verbose=True)

                # Verify that existing roles got the additional permissions
                from cornflow.models import PermissionViewRoleModel

                # Check that VIEWER_ROLE has additional permissions
                viewer_permissions = PermissionViewRoleModel.query.filter_by(
                    role_id=VIEWER_ROLE
                ).all()
                self.assertTrue(len(viewer_permissions) > 0)

                # Check that PLANNER_ROLE has additional permissions
                planner_permissions = PermissionViewRoleModel.query.filter_by(
                    role_id=PLANNER_ROLE
                ).all()
                self.assertTrue(len(planner_permissions) > 0)

    @patch("cornflow.commands.auxiliar.import_module")
    @patch("cornflow.commands.views.import_module")
    @patch("cornflow.commands.permissions.import_module")
    @patch.dict(
        os.environ, {"EXTERNAL_APP": "1", "EXTERNAL_APP_MODULE": "external_test_app"}
    )
    def test_view_update_and_deletion(
        self, mock_import_permissions, mock_import_views, mock_import_auxiliar
    ):
        """
        Test that views are updated when URLs change and deleted when resources are removed
        """
        # === INITIAL SETUP ===
        # Create initial mock external app with 3 endpoints
        mock_external_app_initial = MagicMock()

        # Initial mock endpoints
        mock_production_endpoint = MagicMock()
        mock_production_endpoint.ROLES_WITH_ACCESS = [888]
        mock_production_endpoint.DESCRIPTION = "Production planning endpoint"

        mock_quality_endpoint = MagicMock()
        mock_quality_endpoint.ROLES_WITH_ACCESS = [777]
        mock_quality_endpoint.DESCRIPTION = "Quality control endpoint"

        mock_scheduling_endpoint = MagicMock()
        mock_scheduling_endpoint.ROLES_WITH_ACCESS = [888, 777]
        mock_scheduling_endpoint.DESCRIPTION = "Scheduling optimizer endpoint"

        # Initial resources structure
        initial_resources = [
            {
                "endpoint": "production_planning",
                "urls": "/production-planning/",
                "resource": mock_production_endpoint,
            },
            {
                "endpoint": "quality_control",
                "urls": "/quality-control/",
                "resource": mock_quality_endpoint,
            },
            {
                "endpoint": "scheduling_optimizer",
                "urls": "/scheduling/",
                "resource": mock_scheduling_endpoint,
            },
        ]

        # Mock the shared.const module (no extra permissions)
        mock_shared_initial = MagicMock()
        mock_const_initial = MagicMock()
        mock_const_initial.EXTRA_PERMISSION_ASSIGNATION = []
        mock_shared_initial.const = mock_const_initial
        mock_external_app_initial.shared = mock_shared_initial

        # Mock the endpoints.resources
        mock_endpoints_initial = MagicMock()
        mock_endpoints_initial.resources = initial_resources
        mock_external_app_initial.endpoints = mock_endpoints_initial

        mock_import_permissions.return_value = mock_external_app_initial
        mock_import_views.return_value = mock_external_app_initial
        mock_import_auxiliar.return_value = mock_external_app_initial

        # === INITIAL ACCESS INIT ===
        from cornflow.commands.access import access_init_command
        from cornflow.models import ViewModel

        # Mock the database session for testing - INITIAL SETUP ONLY
        with patch.object(db.session, "commit"):
            with patch.object(db.session, "rollback"):
                # Run initial access initialization
                access_init_command(verbose=True)

                # Verify initial views were created
                initial_views = ViewModel.query.filter(
                    ViewModel.name.in_(
                        [
                            "production_planning",
                            "quality_control",
                            "scheduling_optimizer",
                        ]
                    )
                ).all()

                self.assertEqual(
                    len(initial_views), 3, "Expected 3 initial views to be created"
                )

                # Get initial URLs
                initial_views_dict = {
                    view.name: view.url_rule for view in initial_views
                }
                self.assertEqual(
                    initial_views_dict["production_planning"], "/production-planning/"
                )
                self.assertEqual(
                    initial_views_dict["quality_control"], "/quality-control/"
                )
                self.assertEqual(
                    initial_views_dict["scheduling_optimizer"], "/scheduling/"
                )

        # === MODIFY CONFIGURATION ===
        # Create updated mock external app with:
        # 1. Changed URL for production_planning
        # 2. Changed URL for quality_control
        # 3. Remove scheduling_optimizer entirely
        mock_external_app_updated = MagicMock()

        # Updated resources structure (scheduling_optimizer removed, URLs changed)
        updated_resources = [
            {
                "endpoint": "production_planning",
                "urls": "/new-production-planning/",  # CHANGED URL
                "resource": mock_production_endpoint,
            },
            {
                "endpoint": "quality_control",
                "urls": "/quality-control/",
                "resource": mock_quality_endpoint,
            },
            # scheduling_optimizer REMOVED entirely
        ]

        # Mock shared const (still no extra permissions)
        mock_shared_updated = MagicMock()
        mock_const_updated = MagicMock()
        mock_const_updated.EXTRA_PERMISSION_ASSIGNATION = []  # Empty list
        mock_shared_updated.const = mock_const_updated
        mock_external_app_updated.shared = mock_shared_updated

        # Mock updated endpoints.resources
        mock_endpoints_updated = MagicMock()
        mock_endpoints_updated.resources = updated_resources
        mock_external_app_updated.endpoints = mock_endpoints_updated

        # Update mocks to return updated configuration
        mock_import_permissions.return_value = mock_external_app_updated
        mock_import_views.return_value = mock_external_app_updated
        mock_import_auxiliar.return_value = mock_external_app_updated

        # === SECOND ACCESS INIT (with updated config) ===
        # Allow real commits for the update to be persisted
        access_init_command(verbose=True)

        # === VERIFY UPDATES ===
        # Check that URLs were updated
        updated_views = ViewModel.query.filter(
            ViewModel.name.in_(["production_planning", "quality_control"])
        ).all()

        self.assertEqual(
            len(updated_views), 2, "Expected 2 views to remain after update"
        )

        updated_views_dict = {view.name: view.url_rule for view in updated_views}
        self.assertEqual(
            updated_views_dict["production_planning"],
            "/new-production-planning/",
            "production_planning URL should be updated",
        )
        self.assertEqual(
            updated_views_dict["quality_control"],
            "/quality-control/",
            "quality_control URL should be updated",
        )

        # === VERIFY DELETION ===
        # Check that scheduling_optimizer view was deleted
        deleted_view = ViewModel.query.filter_by(name="scheduling_optimizer").first()
        self.assertIsNone(deleted_view, "scheduling_optimizer view should be deleted")

        # === VERIFY PERMISSIONS ARE CLEANED UP ===
        from cornflow.models import PermissionViewRoleModel

        # Check that permissions for deleted view are cleaned up
        remaining_permissions = PermissionViewRoleModel.query.all()
        scheduling_permissions = [
            perm
            for perm in remaining_permissions
            if perm.api_view and perm.api_view.name == "scheduling_optimizer"
        ]
        self.assertEqual(
            len(scheduling_permissions),
            0,
            "All permissions for deleted scheduling_optimizer view should be removed",
        )

        # Check that permissions for remaining views still exist
        remaining_external_permissions = [
            perm
            for perm in remaining_permissions
            if perm.api_view
            and perm.api_view.name in ["production_planning", "quality_control"]
        ]

        all_view_names = [
            perm.api_view.name for perm in remaining_permissions if perm.api_view
        ]
        self.assertTrue(
            len(remaining_external_permissions) > 0,
            f"Permissions for remaining views should still exist. Found views: {set(all_view_names)}",
        )


if __name__ == "__main__":
    unittest.main()
