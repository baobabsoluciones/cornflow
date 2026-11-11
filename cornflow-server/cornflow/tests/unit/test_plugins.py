"""
Tests for the access initialization in plugin mode.

``access_init`` must keep the views mounted by the plugins while it keeps
deleting the obsolete core views, it must ask each plugin to register its own
access, by priority, and it must leave the permissions on the views of each
plugin exactly as the code declares them.
"""

import importlib.metadata
from unittest.mock import patch

from flask_restful import Api

from cornflow.app import create_app
from cornflow.commands import access_init_command
from cornflow.commands.auxiliar import get_all_external, get_all_resources
from cornflow.commands.permissions import (
    get_base_permissions,
    get_db_permissions,
    get_permissions_in_code_as_tuples,
    get_permissions_to_register,
    save_and_delete_permissions,
)
from cornflow.commands.views import (
    get_database_view,
    get_views_to_register,
    load_changes_to_db,
)
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import (
    PermissionViewRoleModel,
    RoleModel,
    UserModel,
    UserRoleModel,
    ViewModel,
)
from cornflow.shared import db
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import (
    ADMIN_ROLE,
    DELETE_ACTION,
    GET_ACTION,
    PLANNER_ROLE,
    POST_ACTION,
    VIEWER_ROLE,
)
from cornflow.shared.plugins import (
    CornflowPlugin,
    get_loaded_plugins,
    get_plugins_resources,
)
from cornflow.tests.custom_test_case import CustomTestCase

PLUGIN_URL = "/test-plugin/items/"
OTHER_PLUGIN_URL = "/other-plugin/items/"
CUSTOM_ROLE_PLUGIN_URL = "/custom-role-plugin/items/"
PLUGIN_CUSTOM_ROLE = 50


class PluginItemsEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [PLANNER_ROLE, ADMIN_ROLE]
    DESCRIPTION = "Items of the test plugin"

    @authenticate(auth_class=Auth())
    def get(self):
        return {"items": []}, 200


class OtherPluginItemsEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [PLANNER_ROLE]
    DESCRIPTION = "Items of the other test plugin"

    @authenticate(auth_class=Auth())
    def get(self):
        return {"items": []}, 200


class CustomRoleItemsEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [PLUGIN_CUSTOM_ROLE]
    DESCRIPTION = "Items of the test plugin with its own role"

    @authenticate(auth_class=Auth())
    def get(self):
        return {"items": []}, 200


def _register_resources_access(app, resources, custom_roles_actions=None):
    """Registers the views and the missing permissions of some resources."""
    with app.app_context():
        views_in_db = get_database_view()
        to_register, _ = get_views_to_register(resources, views_in_db)
        load_changes_to_db([], to_register, [])
        views_in_db = {v.name: v.id for v in ViewModel.get_all_objects()}
        base_permissions = get_base_permissions(
            {r["endpoint"]: r["resource"].ROLES_WITH_ACCESS for r in resources},
            custom_roles_actions or {},
        )
        _, permissions_in_db_keys = get_db_permissions()
        tuples = get_permissions_in_code_as_tuples(
            resources, views_in_db, base_permissions, []
        )
        save_and_delete_permissions(
            get_permissions_to_register(tuples, permissions_in_db_keys), []
        )


class ResourcesPlugin(CornflowPlugin):
    """Test plugin that mounts its own resources and registers its access."""

    priority = 20
    url = PLUGIN_URL
    endpoint = "test-plugin-items"
    resource = PluginItemsEndpoint
    calls = []

    def init_app(self, app):
        Api(app).add_resource(self.resource, self.url, endpoint=self.endpoint)

    def register_access(self, app):
        self.calls.append(type(self).__name__)
        _register_resources_access(
            app,
            [{"endpoint": self.endpoint, "urls": self.url, "resource": self.resource}],
        )


class OtherResourcesPlugin(ResourcesPlugin):
    priority = 10
    url = OTHER_PLUGIN_URL
    endpoint = "other-plugin-items"
    resource = OtherPluginItemsEndpoint


class CustomRolePlugin(ResourcesPlugin):
    """Test plugin that declares its own role."""

    url = CUSTOM_ROLE_PLUGIN_URL
    endpoint = "custom-role-plugin-items"
    resource = CustomRoleItemsEndpoint
    custom_roles_actions = {PLUGIN_CUSTOM_ROLE: [GET_ACTION, POST_ACTION]}

    def register_access(self, app):
        if RoleModel.query.get(PLUGIN_CUSTOM_ROLE) is None:
            RoleModel({"id": PLUGIN_CUSTOM_ROLE, "name": "plugin_role"}).save()
        _register_resources_access(
            app,
            [{"endpoint": self.endpoint, "urls": self.url, "resource": self.resource}],
            self.custom_roles_actions,
        )

    def get_custom_roles_actions(self):
        return self.custom_roles_actions


class PluginWithoutAccess:
    """Plugin that does not inherit the base class nor registers its access."""

    def init_app(self, app):
        Api(app).add_resource(
            OtherPluginItemsEndpoint, OTHER_PLUGIN_URL, endpoint="other-plugin-items"
        )


class FakeEntryPoint:
    def __init__(self, name, plugin_class):
        self.name = name
        self.plugin_class = plugin_class

    def load(self):
        return self.plugin_class


class PluginAccessTestCase(CustomTestCase):
    """The application is created with the given plugins, in this order."""

    PLUGINS = [("test_plugin", ResourcesPlugin)]

    def create_app(self):
        original = importlib.metadata.entry_points
        entry_points = [FakeEntryPoint(name, cls) for name, cls in self.PLUGINS]

        def fake_entry_points(**kwargs):
            if kwargs.get("group") == "cornflow.plugins":
                return entry_points
            return original(**kwargs)

        with patch.object(importlib.metadata, "entry_points", fake_entry_points):
            return create_app("testing")

    def setUp(self):
        ResourcesPlugin.calls.clear()
        super().setUp()

    @staticmethod
    def snapshot():
        views = {v.name: (v.id, v.url_rule) for v in ViewModel.get_all_objects()}
        permissions = {
            (p.role_id, p.action_id, p.api_view_id)
            for p in PermissionViewRoleModel.get_all_objects()
        }
        return views, permissions

    @staticmethod
    def view_permissions(view_name):
        view = ViewModel.query.filter_by(name=view_name).first()
        return {
            (p.role_id, p.action_id)
            for p in PermissionViewRoleModel.query.filter_by(api_view_id=view.id)
        }


class TestPluginAccess(PluginAccessTestCase):
    def test_plugin_resources_recorded(self):
        resources = get_plugins_resources(self.app)
        self.assertEqual(
            [("test-plugin-items", PLUGIN_URL, PluginItemsEndpoint)],
            [(r["endpoint"], r["urls"], r["resource"]) for r in resources],
        )

    def test_access_init_registers_plugin_view_and_permissions(self):
        view = ViewModel.query.filter_by(name="test-plugin-items").first()
        self.assertIsNotNone(view)
        self.assertEqual(PLUGIN_URL, view.url_rule)
        self.assertIn(
            (PLANNER_ROLE, GET_ACTION), self.view_permissions("test-plugin-items")
        )

    def test_access_init_keeps_plugin_views_and_permissions(self):
        before = self.snapshot()
        access_init_command(verbose=False)
        access_init_command(verbose=False)
        self.assertEqual(before, self.snapshot())

    def test_plugin_endpoint_not_forbidden_after_access_init(self):
        token = self.create_planner()
        headers = self.get_header_with_auth(token)
        self.assertEqual(200, self.client.get(PLUGIN_URL, headers=headers).status_code)
        access_init_command(verbose=False)
        access_init_command(verbose=False)
        self.assertEqual(200, self.client.get(PLUGIN_URL, headers=headers).status_code)

    def test_access_init_deletes_obsolete_core_views(self):
        obsolete = ViewModel(
            {
                "name": "obsolete-core-view",
                "url_rule": "/cornflow/obsolete/",
                "description": "A core view no longer in the code",
            }
        )
        obsolete.save()
        PermissionViewRoleModel(
            {"role_id": PLANNER_ROLE, "action_id": GET_ACTION, "api_view_id": obsolete.id}
        ).save()
        access_init_command(verbose=False)
        self.assertIsNone(ViewModel.query.filter_by(name="obsolete-core-view").first())
        self.assertIsNotNone(ViewModel.query.filter_by(name="test-plugin-items").first())

    def test_custom_permission_on_plugin_view_deleted_on_init(self):
        view_id = ViewModel.query.filter_by(name="test-plugin-items").first().id
        PermissionViewRoleModel(
            {"role_id": VIEWER_ROLE, "action_id": GET_ACTION, "api_view_id": view_id}
        ).save()
        headers = self.get_header_with_auth(self.create_user_with_role(VIEWER_ROLE))
        # Only the viewer role: the default role on sign up is removed
        user_id = UserModel.query.filter_by(username=f"testuser{VIEWER_ROLE}").first().id
        UserRoleModel.query.filter_by(user_id=user_id, role_id=PLANNER_ROLE).delete()
        db.session.commit()
        self.assertEqual(200, self.client.get(PLUGIN_URL, headers=headers).status_code)
        access_init_command(verbose=False)
        self.assertNotIn(
            (VIEWER_ROLE, GET_ACTION), self.view_permissions("test-plugin-items")
        )
        self.assertEqual(403, self.client.get(PLUGIN_URL, headers=headers).status_code)

    def test_role_removed_from_declaration_loses_permission_on_init(self):
        self.assertIn(
            (ADMIN_ROLE, GET_ACTION), self.view_permissions("test-plugin-items")
        )
        with patch.object(PluginItemsEndpoint, "ROLES_WITH_ACCESS", [PLANNER_ROLE]):
            access_init_command(verbose=False)
        permissions = self.view_permissions("test-plugin-items")
        self.assertFalse(any(role == ADMIN_ROLE for role, _ in permissions))
        self.assertIn((PLANNER_ROLE, GET_ACTION), permissions)

    def test_declared_permission_deleted_by_hand_is_restored_on_init(self):
        view_id = ViewModel.query.filter_by(name="test-plugin-items").first().id
        before = self.snapshot()
        PermissionViewRoleModel.query.filter_by(
            role_id=PLANNER_ROLE, action_id=GET_ACTION, api_view_id=view_id
        ).first().delete()
        self.assertNotIn(
            (PLANNER_ROLE, GET_ACTION), self.view_permissions("test-plugin-items")
        )
        access_init_command(verbose=False)
        self.assertEqual(before, self.snapshot())

    def test_plugin_view_permissions_are_the_declared_ones(self):
        resource = {
            "endpoint": "test-plugin-items",
            "urls": PLUGIN_URL,
            "resource": PluginItemsEndpoint,
        }
        view_id = ViewModel.query.filter_by(name="test-plugin-items").first().id
        expected = get_permissions_in_code_as_tuples(
            [resource],
            {"test-plugin-items": view_id},
            get_base_permissions(get_all_resources([resource]), {}),
            [],
        )
        self.assertEqual(
            {(role, action) for role, action, _ in expected},
            self.view_permissions("test-plugin-items"),
        )

    def test_core_view_permissions_are_the_declared_ones(self):
        core_resources, extra_permissions, _ = get_all_external(None)
        views_in_db = {v.name: v.id for v in ViewModel.get_all_objects()}
        expected = get_permissions_in_code_as_tuples(
            core_resources,
            views_in_db,
            get_base_permissions(get_all_resources(core_resources), {}),
            extra_permissions,
        )
        plugin_view_id = views_in_db["test-plugin-items"]
        stored = {
            permission
            for permission in self.snapshot()[1]
            if permission[2] != plugin_view_id
        }
        self.assertEqual(expected, stored)

    def test_custom_permission_on_core_view_is_still_reset(self):
        view_id = ViewModel.query.filter_by(name="instance").first().id
        PermissionViewRoleModel(
            {"role_id": VIEWER_ROLE, "action_id": DELETE_ACTION, "api_view_id": view_id}
        ).save()
        access_init_command(verbose=False)
        self.assertNotIn((VIEWER_ROLE, DELETE_ACTION), self.view_permissions("instance"))

    def test_register_access_is_idempotent(self):
        before = self.snapshot()
        plugin = get_loaded_plugins(self.app)[0].plugin
        plugin.register_access(self.app)
        plugin.register_access(self.app)
        self.assertEqual(before, self.snapshot())


class TestPluginAccessPriority(PluginAccessTestCase):
    # Discovered in the opposite order to their priority
    PLUGINS = [("test_plugin", ResourcesPlugin), ("other_plugin", OtherResourcesPlugin)]

    def test_access_registered_by_priority(self):
        self.assertEqual(["OtherResourcesPlugin", "ResourcesPlugin"], ResourcesPlugin.calls)
        ResourcesPlugin.calls.clear()
        access_init_command(verbose=False)
        self.assertEqual(["OtherResourcesPlugin", "ResourcesPlugin"], ResourcesPlugin.calls)

    def test_loaded_plugins_sorted_by_priority(self):
        self.assertEqual(
            ["other_plugin", "test_plugin"],
            [p.name for p in get_loaded_plugins(self.app)],
        )

    def test_both_plugins_keep_their_views(self):
        before = self.snapshot()
        access_init_command(verbose=False)
        self.assertEqual(before, self.snapshot())
        for name in ("test-plugin-items", "other-plugin-items"):
            self.assertIn(name, before[0])


class TestPluginWithCustomRole(PluginAccessTestCase):
    PLUGINS = [("custom_role_plugin", CustomRolePlugin)]

    def test_custom_role_gets_the_declared_actions(self):
        self.assertEqual(
            {(PLUGIN_CUSTOM_ROLE, GET_ACTION), (PLUGIN_CUSTOM_ROLE, POST_ACTION)},
            self.view_permissions("custom-role-plugin-items"),
        )

    def test_action_removed_from_custom_role_is_deleted_on_init(self):
        with patch.object(
            CustomRolePlugin,
            "custom_roles_actions",
            {PLUGIN_CUSTOM_ROLE: [GET_ACTION]},
        ):
            access_init_command(verbose=False)
        self.assertEqual(
            {(PLUGIN_CUSTOM_ROLE, GET_ACTION)},
            self.view_permissions("custom-role-plugin-items"),
        )

    def test_undefined_custom_role_actions_leave_permissions_untouched(self):
        before = self.snapshot()
        with patch.object(CustomRolePlugin, "get_custom_roles_actions", lambda self: {}):
            # register_access itself needs the actions, so it is skipped here
            with patch.object(CustomRolePlugin, "register_access", lambda self, app: None):
                access_init_command(verbose=False)
        self.assertEqual(before, self.snapshot())


class TestPluginsOnlySyncTheirViews(PluginAccessTestCase):
    PLUGINS = [("test_plugin", ResourcesPlugin), ("plain_plugin", PluginWithoutAccess)]

    def test_hand_permission_on_a_view_of_a_plugin_without_access_survives(self):
        view_id = ViewModel.query.filter_by(name="other-plugin-items").first().id
        PermissionViewRoleModel(
            {"role_id": VIEWER_ROLE, "action_id": GET_ACTION, "api_view_id": view_id}
        ).save()
        test_view_id = ViewModel.query.filter_by(name="test-plugin-items").first().id
        PermissionViewRoleModel(
            {"role_id": VIEWER_ROLE, "action_id": GET_ACTION, "api_view_id": test_view_id}
        ).save()
        access_init_command(verbose=False)
        self.assertEqual(
            {(VIEWER_ROLE, GET_ACTION)}, self.view_permissions("other-plugin-items")
        )
        self.assertNotIn(
            (VIEWER_ROLE, GET_ACTION), self.view_permissions("test-plugin-items")
        )


class TestPluginWithoutRegisterAccess(PluginAccessTestCase):
    PLUGINS = [("plain_plugin", PluginWithoutAccess)]

    def test_view_kept_without_permissions(self):
        # The view is kept, but its permissions are left to the plugin itself
        self.assertIsNotNone(ViewModel.query.filter_by(name="other-plugin-items").first())
        self.assertEqual(set(), self.view_permissions("other-plugin-items"))
        access_init_command(verbose=False)
        self.assertIsNotNone(ViewModel.query.filter_by(name="other-plugin-items").first())

    def test_permissions_registered_by_the_plugin_survive(self):
        _register_resources_access(
            self.app,
            [
                {
                    "endpoint": "other-plugin-items",
                    "urls": OTHER_PLUGIN_URL,
                    "resource": OtherPluginItemsEndpoint,
                }
            ],
        )
        before = self.snapshot()
        access_init_command(verbose=False)
        self.assertEqual(before, self.snapshot())


class TestNoPlugins(PluginAccessTestCase):
    PLUGINS = []

    def test_no_plugin_resources(self):
        self.assertEqual([], get_plugins_resources(self.app))
        self.assertEqual([], get_loaded_plugins(self.app))
