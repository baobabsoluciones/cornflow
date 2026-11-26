"""
Tests of the administration rights that depend on the security level (task008):

- permissions of the client admin (role 3) on the access-management views and
  on the unlock endpoint, registered by access_init according to the level;
- management of roles, permissions, actions and views, with the reserved role
  range (900-999) kept for the platform administrator at every level;
- grant and revoke of roles (the admin role can be revoked by a client admin
  only at level 1; platform roles only by a platform administrator);
- user sign up (admin at level 1, platform administrator from level 2);
- unlock of accounts (client admin at levels 1 and 2 for users without
  platform roles, platform administrator for anyone, CLI at every level).

The expected values and messages are written in this file on purpose: they
come from the specification, not from the code under test. The helpers of the
new code are reached through their modules, so that this file can be imported
(and the cases that do not use them still run) before they exist.
"""

import json
import logging
import unittest
from importlib import import_module
from unittest.mock import patch

from click.testing import CliRunner
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.commands.access import access_init_command
from cornflow.models import (
    PermissionViewRoleModel,
    RoleModel,
    UserModel,
    UserRoleModel,
    ViewModel,
)
from cornflow.shared import const, db
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_VIEWER_ROLE,
    VIEWER_ROLE,
)
from cornflow.shared.exceptions import ConfigurationError
from cornflow.shared.security_levels import SECURITY_LEVELS
from cornflow.tests.const import (
    ACTIONS_URL,
    APIVIEW_URL,
    LOGIN_URL,
    PERMISSION_URL,
    ROLES_URL,
    SIGNUP_URL,
    USER_ROLE_URL,
    USER_URL,
)
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    security_level_config,
)
from cornflow.tests.unit import test_security_startup as startup

P = "Kx9#tR2m!Qw7Zp"  # valid at the three levels
JSON_HEADER = {"Content-Type": "application/json"}

# Actions
GET, PATCH, POST, PUT, DELETE = 1, 2, 3, 4, 5

ACCESS_VIEWS = (
    "roles",
    "roles-detail",
    "permissions",
    "permission-detail",
    "actions",
    "api-view",
)
UNLOCK_VIEW = "user-unlock"

TABLE_DENIED = "You do not have permission to access this endpoint"
RESERVED_ROLE_ERROR = (
    "Role ids 900-999 are reserved for the cornflow platform roles: only a "
    "platform administrator can manage them"
)
RESERVED_ROLE_ID_ERROR = (
    "Role ids 900-999 are reserved for the cornflow platform roles and a custom "
    "role there would stop cornflow from starting: leave the id out or use an "
    "id outside 900-999"
)
NO_FREE_ROLE_ID_ERROR = (
    "There is no free role id below 900: create the role with an explicit id "
    "outside 900-999"
)
PLATFORM_ROLE_PERMISSION_ERROR = (
    "Only a platform administrator can manage the permissions of the platform roles"
)
REVOKE_ROLE_ERROR = "Only a platform administrator can revoke this role"
REVOKE_ADMIN_ERROR = (
    "Only a platform administrator can revoke the admin role from a user"
)
UNLOCK_PLATFORM_USER_ERROR = (
    "Only a platform administrator can unlock the account of a platform user"
)
UNLOCKED_MESSAGE = "The user account has been unlocked"
SIGNUP_RESTRICTED_ERROR = "Only a platform administrator can create users on this deployment"


def level_overrides(level):
    # Level 3 requires MFA by default; these cases do not enroll it
    return {"MFA_REQUIRED": 0} if level == 3 else {}


def admin_access():
    """The new helpers module, imported when a test needs it."""
    return import_module("cornflow.shared.admin_access")


def level_table(level):
    return list(const.LEVEL_PERMISSION_ASSIGNATION[level])


def expected_level_1_tuples():
    tuples = {(ADMIN_ROLE, action, view) for view in ACCESS_VIEWS for action in range(1, 6)}
    tuples.add((ADMIN_ROLE, PUT, UNLOCK_VIEW))
    return tuples


EXPECTED_LEVEL_TUPLES = {
    1: expected_level_1_tuples(),
    2: {(ADMIN_ROLE, PUT, UNLOCK_VIEW)},
    3: set(),
}


class _AuditCapture(logging.Handler):
    """Captures the JSON records emitted on the cornflow.audit logger."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        try:
            self.records.append(json.loads(record.getMessage()))
        except (ValueError, TypeError):
            pass

    def by_event(self, event):
        return [r for r in self.records if r.get("event") == event]


# --------------------------------------------------------------------------
# A. Declarative table and helpers
# --------------------------------------------------------------------------
class TestLevelPermissionTable(unittest.TestCase):
    def test_table_has_one_entry_per_level(self):
        self.assertEqual(set(SECURITY_LEVELS), set(const.LEVEL_PERMISSION_ASSIGNATION))

    def test_level_1(self):
        table = level_table(1)
        self.assertEqual(31, len(table))
        self.assertEqual(31, len(set(table)))
        self.assertEqual(EXPECTED_LEVEL_TUPLES[1], set(table))

    def test_level_2(self):
        self.assertEqual([(ADMIN_ROLE, PUT, UNLOCK_VIEW)], level_table(2))

    def test_level_3(self):
        self.assertEqual([], level_table(3))

    def test_only_admin_role_and_known_views(self):
        views = set(ACCESS_VIEWS) | {UNLOCK_VIEW}
        for level in (1, 2, 3):
            for role, action, view in level_table(level):
                with self.subTest(level=level, permission=(role, action, view)):
                    self.assertEqual(ADMIN_ROLE, role)
                    self.assertIn(view, views)
                    self.assertIn(action, range(1, 6))

    def test_access_management_endpoints(self):
        self.assertEqual(ACCESS_VIEWS, tuple(const.ACCESS_MANAGEMENT_ENDPOINTS))

    def test_admin_base_actions(self):
        self.assertEqual((1, 2, 3, 4, 5), tuple(const.ADMIN_BASE_ACTIONS))

    def test_client_admin_revoke_admin_max_level(self):
        self.assertEqual(1, const.CLIENT_ADMIN_REVOKE_ADMIN_MAX_LEVEL)

    def test_strictest_security_level(self):
        self.assertEqual(3, const.STRICTEST_SECURITY_LEVEL)


class TestAdminAccessHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = {
            level: create_app(security_level_config(level, **level_overrides(level)))
            for level in (1, 2, 3)
        }

    def test_level_permission_assignation_sizes(self):
        helpers = admin_access()
        for level, size in ((1, 31), (2, 1), (3, 0)):
            with self.subTest(level=level):
                result = helpers.level_permission_assignation(level)
                self.assertEqual(size, len(result))
                self.assertEqual(EXPECTED_LEVEL_TUPLES[level], set(result))

    def test_level_permission_assignation_returns_a_copy(self):
        helpers = admin_access()
        result = helpers.level_permission_assignation(1)
        result.append((1, 1, "x"))
        result.clear()
        self.assertEqual(31, len(const.LEVEL_PERMISSION_ASSIGNATION[1]))
        self.assertEqual(31, len(helpers.level_permission_assignation(1)))

    def test_level_permission_assignation_unknown_level(self):
        self.assertEqual([], admin_access().level_permission_assignation(4))

    def test_level_permission_assignation_follows_the_app_level(self):
        helpers = admin_access()
        for level, size in ((1, 31), (2, 1), (3, 0)):
            with self.subTest(level=level), self.apps[level].app_context():
                self.assertEqual(size, len(helpers.level_permission_assignation()))

    def test_current_security_level_without_context(self):
        self.assertEqual(3, admin_access().current_security_level())

    def test_current_security_level_with_app(self):
        helpers = admin_access()
        for level in (1, 2, 3):
            with self.subTest(level=level), self.apps[level].app_context():
                self.assertEqual(level, helpers.current_security_level())

    def test_current_security_level_invalid_values(self):
        helpers = admin_access()
        app = self.apps[1]
        original = app.config["SECURITY_LEVEL"]
        try:
            with app.app_context():
                app.config.pop("SECURITY_LEVEL")
                self.assertEqual(3, helpers.current_security_level())
                for value in (None, "abc", 7):
                    with self.subTest(value=value):
                        app.config["SECURITY_LEVEL"] = value
                        self.assertEqual(3, helpers.current_security_level())
                app.config["SECURITY_LEVEL"] = "2"
                self.assertEqual(2, helpers.current_security_level())
        finally:
            app.config["SECURITY_LEVEL"] = original

    def test_client_admin_can_revoke_admin(self):
        helpers = admin_access()
        self.assertTrue(helpers.client_admin_can_revoke_admin(1))
        self.assertFalse(helpers.client_admin_can_revoke_admin(2))
        self.assertFalse(helpers.client_admin_can_revoke_admin(3))
        self.assertFalse(helpers.client_admin_can_revoke_admin(4))

    def test_client_admin_can_revoke_admin_follows_the_app_level(self):
        helpers = admin_access()
        for level, expected in ((1, True), (2, False), (3, False)):
            with self.subTest(level=level), self.apps[level].app_context():
                self.assertEqual(expected, helpers.client_admin_can_revoke_admin())

    def test_client_admin_can_revoke_admin_without_context(self):
        self.assertFalse(admin_access().client_admin_can_revoke_admin())

    def test_is_reserved_role_id(self):
        helpers = admin_access()
        for value in (900, 950, 999, "950"):
            with self.subTest(value=value):
                self.assertTrue(helpers.is_reserved_role_id(value))
        for value in (899, 1000, 0, 5, None, "abc"):
            with self.subTest(value=value):
                self.assertFalse(helpers.is_reserved_role_id(value))


# --------------------------------------------------------------------------
# Common base of the cases that run against an application of each level
# --------------------------------------------------------------------------
class _AdminLevelCases:
    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        self.admin = self.make_user("cfadmin", ADMIN_ROLE)
        self.admin2 = self.make_user("cfadmin2", ADMIN_ROLE)
        self.platform_admin = self.make_user("cfplatform", PLATFORM_ADMIN_ROLE)
        self.planner = self.make_user("cfplanner", PLANNER_ROLE)
        self.platform_viewer = self.make_user("cfpviewer", PLATFORM_VIEWER_ROLE)
        self.audit_logger = logging.getLogger("cornflow.audit")
        self._previous_level = self.audit_logger.level
        self.audit_logger.setLevel(logging.INFO)
        self.capture = _AuditCapture()
        self.audit_logger.addHandler(self.capture)

    def tearDown(self):
        self.audit_logger.removeHandler(self.capture)
        self.audit_logger.setLevel(self._previous_level)
        db.session.remove()
        db.drop_all()

    # helpers
    def make_user(self, username, role):
        user = UserModel(
            {"username": username, "email": f"{username}@test.org", "password": P}
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role}).save()
        return user

    def token(self, username):
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": P}),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, response.status_code, response.json)
        return response.json["token"]

    def headers(self, username):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token(username)}",
        }

    def request(self, method, url, username, body=None):
        kwargs = {"headers": self.headers(username)}
        if body is not None:
            kwargs["data"] = json.dumps(body)
        return getattr(self.client, method)(url, **kwargs)

    def lock(self, user):
        user.locked = True
        user.failed_login_attempts = 5
        user.save()

    def fresh_user(self, username):
        db.session.expire_all()
        return UserModel.get_one_user_by_username(username)

    def view_id(self, name):
        return ViewModel.query.filter_by(name=name).first().id

    def permission_of(self, role_id, view_name=None):
        query = PermissionViewRoleModel.query.filter_by(role_id=role_id)
        if view_name is not None:
            query = query.filter_by(api_view_id=self.view_id(view_name))
        return query.first()

    def all_permission_tuples(self):
        db.session.expire_all()
        return {
            (p.role_id, p.action_id, p.api_view_id)
            for p in PermissionViewRoleModel.query.all()
        }

    def admin_level_permissions(self):
        """(action_id, view name) of role 3 on the access views and on user-unlock."""
        db.session.expire_all()
        names = set(ACCESS_VIEWS) | {UNLOCK_VIEW}
        return {
            (p.action_id, p.api_view.name)
            for p in PermissionViewRoleModel.query.all()
            if p.role_id == ADMIN_ROLE and p.api_view.name in names
        }

    def assert_table_denied(self, response):
        self.assertEqual(403, response.status_code, response.json)
        self.assertEqual(TABLE_DENIED, response.json["error"])

    def assert_error(self, response, status, message):
        self.assertEqual(status, response.status_code, response.json)
        self.assertEqual(message, response.json["error"])


class _LevelCase(_AdminLevelCases, SecurityLevelTestMixin, TestCase):
    """Concrete base: subclasses set security_level."""


# --------------------------------------------------------------------------
# B. Registration by level
# --------------------------------------------------------------------------
class _RegisterCases:
    expected = None

    def test_admin_permissions_registered(self):
        expected = {(a, v) for _, a, v in EXPECTED_LEVEL_TUPLES[self.security_level]}
        self.assertEqual(expected, self.admin_level_permissions())

    def test_admin_level_permission_count(self):
        sizes = {1: 31, 2: 1, 3: 0}
        self.assertEqual(sizes[self.security_level], len(self.admin_level_permissions()))

    def test_platform_admin_has_everything(self):
        db.session.expire_all()
        names = set(ACCESS_VIEWS) | {UNLOCK_VIEW}
        granted = {
            (p.action_id, p.api_view.name)
            for p in PermissionViewRoleModel.query.all()
            if p.role_id == PLATFORM_ADMIN_ROLE and p.api_view.name in names
        }
        for view in ACCESS_VIEWS:
            for action in range(1, 6):
                with self.subTest(view=view, action=action):
                    self.assertIn((action, view), granted)
        self.assertIn((PUT, UNLOCK_VIEW), granted)

    def test_running_access_init_again_changes_nothing(self):
        before = self.all_permission_tuples()
        count = PermissionViewRoleModel.query.count()
        access_init_command(verbose=False)
        self.assertEqual(count, PermissionViewRoleModel.query.count())
        self.assertEqual(before, self.all_permission_tuples())

    def test_extra_permission_assignation_is_not_mutated(self):
        length = len(const.EXTRA_PERMISSION_ASSIGNATION)
        access_init_command(verbose=False)
        self.assertEqual(length, len(const.EXTRA_PERMISSION_ASSIGNATION))


class TestRegisterLevelPermissionsLevel1(_RegisterCases, _LevelCase):
    security_level = 1
    config_overrides = level_overrides(1)


class TestRegisterLevelPermissionsLevel2(_RegisterCases, _LevelCase):
    security_level = 2
    config_overrides = level_overrides(2)


class TestRegisterLevelPermissionsLevel3(_RegisterCases, _LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)


# --------------------------------------------------------------------------
# C. Level change
# --------------------------------------------------------------------------
class TestLevelChange(_LevelCase):
    security_level = 1

    def switch_to(self, level):
        original = self.app.config["SECURITY_LEVEL"]
        self.addCleanup(self.app.config.__setitem__, "SECURITY_LEVEL", original)
        self.app.config["SECURITY_LEVEL"] = level
        access_init_command(verbose=False)

    def level_tuples(self, level):
        """The (role, action, view id) tuples that a level adds, with view ids."""
        return {
            (role, action, self.view_id(view))
            for role, action, view in EXPECTED_LEVEL_TUPLES[level]
        }

    def test_1_to_3(self):
        before = self.all_permission_tuples()
        self.assertTrue(self.level_tuples(1) <= before)
        self.switch_to(3)
        self.assertEqual(before - self.level_tuples(1), self.all_permission_tuples())

    def test_3_to_1(self):
        self.switch_to(3)
        before = self.all_permission_tuples()
        self.switch_to(1)
        self.assertEqual(before | self.level_tuples(1), self.all_permission_tuples())
        self.assertEqual(31, len(self.admin_level_permissions()))

    def test_1_to_2(self):
        before = self.all_permission_tuples()
        self.switch_to(2)
        removed = self.level_tuples(1) - self.level_tuples(2)
        self.assertEqual(30, len(removed))
        self.assertEqual(before - removed, self.all_permission_tuples())
        self.assertEqual({(PUT, UNLOCK_VIEW)}, self.admin_level_permissions())

    def test_2_to_1(self):
        self.switch_to(2)
        before = self.all_permission_tuples()
        self.switch_to(1)
        added = self.all_permission_tuples() - before
        self.assertEqual(30, len(added))
        self.assertEqual(before | added, self.all_permission_tuples())
        self.assertEqual(31, len(self.admin_level_permissions()))

    def test_manual_permission_is_deleted_on_the_next_registration(self):
        # Contract (behaviour of always): what is not in the code is deleted
        response = self.request(
            "post",
            PERMISSION_URL,
            "cfplatform",
            {"role_id": VIEWER_ROLE, "action_id": GET, "api_view_id": self.view_id("roles")},
        )
        self.assertEqual(201, response.status_code, response.json)
        manual = (VIEWER_ROLE, GET, self.view_id("roles"))
        self.assertIn(manual, self.all_permission_tuples())
        access_init_command(verbose=False)
        self.assertNotIn(manual, self.all_permission_tuples())


class TestServiceInitLevelPermissions(TestCase):
    # The class of task002 is reached through its module so that unittest does
    # not collect (and run again) its tests from this module.
    ADMIN_PWD = "Granito-Vela-Oruga7"
    SERVICE_PWD = "Mimbre-Faro-Ciervo4"

    run_init = startup.TestServiceInitSecurity.run_init
    gunicorn_started = staticmethod(startup.TestServiceInitSecurity.gunicorn_started)

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def admin_permissions(self):
        db.session.expire_all()
        return {
            (p.action_id, p.api_view.name)
            for p in PermissionViewRoleModel.query.all()
            if p.role_id == ADMIN_ROLE
            and p.api_view.name in set(ACCESS_VIEWS) | {UNLOCK_VIEW}
        }

    def test_level_changes_between_starts(self):
        result, system, _ = self.run_init(1)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(self.gunicorn_started(system))
        self.assertIn((POST, "roles"), self.admin_permissions())

        result, system, _ = self.run_init(3, MFA_REQUIRED=0)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(self.gunicorn_started(system))
        self.assertNotIn((POST, "roles"), self.admin_permissions())
        self.assertEqual(set(), self.admin_permissions())

        result, system, _ = self.run_init(2)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual({(PUT, UNLOCK_VIEW)}, self.admin_permissions())


# --------------------------------------------------------------------------
# D. Roles, permissions, actions and API views
# --------------------------------------------------------------------------
class _AccessManagementPlatformCases:
    """Same at every level: platform administrator and planner."""

    def test_platform_creates_role_below_reserved_range(self):
        response = self.request("post", ROLES_URL, "cfplatform", {"name": "p"})
        self.assertEqual(201, response.status_code, response.json)
        self.assertLess(response.json["id"], 900)
        self.assertEqual("p", response.json["name"])
        self.assertIsNotNone(RoleModel.query.get(response.json["id"]))

    def test_platform_cannot_create_role_in_reserved_range(self):
        response = self.request("post", ROLES_URL, "cfplatform", {"id": 950, "name": "x"})
        self.assert_error(response, 400, RESERVED_ROLE_ID_ERROR)
        self.assertIsNone(RoleModel.query.get(950))

    def test_platform_creates_role_with_explicit_id(self):
        response = self.request("post", ROLES_URL, "cfplatform", {"id": 10, "name": "r10"})
        self.assertEqual(201, response.status_code, response.json)
        self.assertEqual(10, response.json["id"])

    def test_platform_edits_reserved_role(self):
        response = self.request(
            "put", f"{ROLES_URL}{PLATFORM_VIEWER_ROLE}/", "cfplatform",
            {"name": RoleModel.query.get(PLATFORM_VIEWER_ROLE).name},
        )
        self.assertEqual(200, response.status_code, response.json)

    def test_platform_edits_reserved_permission(self):
        permission = self.permission_of(902)
        response = self.request(
            "put", f"{PERMISSION_URL}{permission.id}/", "cfplatform",
            {"action_id": permission.action_id},
        )
        self.assertEqual(200, response.status_code, response.json)

    def test_platform_creates_permission_of_platform_role(self):
        view = self.view_id("roles")
        response = self.request(
            "post", PERMISSION_URL, "cfplatform",
            {"role_id": PLATFORM_VIEWER_ROLE, "action_id": GET, "api_view_id": view},
        )
        self.assertEqual(201, response.status_code, response.json)

    def test_platform_reads_access_views(self):
        for url in (ROLES_URL, PERMISSION_URL, ACTIONS_URL, APIVIEW_URL):
            with self.subTest(url=url):
                self.assertEqual(200, self.request("get", url, "cfplatform").status_code)

    def test_access_init_survives_role_created_without_id(self):
        for actor in ("cfplatform",) + (("cfadmin",) if self.security_level == 1 else ()):
            with self.subTest(actor=actor):
                response = self.request("post", ROLES_URL, actor, {"name": f"by_{actor}"})
                self.assertEqual(201, response.status_code, response.json)
                try:
                    access_init_command(verbose=False)
                except ConfigurationError as error:  # pragma: no cover
                    self.fail(f"access_init failed after creating a role: {error}")

    def test_platform_sees_admin_permissions_of_the_level(self):
        response = self.request("get", PERMISSION_URL, "cfplatform")
        self.assertEqual(200, response.status_code)
        expected_access = {1: 30, 2: 0, 3: 0}[self.security_level]
        expected_unlock = {1: 1, 2: 1, 3: 0}[self.security_level]
        admin_rows = [row for row in response.json if row["role_id"] == ADMIN_ROLE]
        self.assertEqual(
            expected_access,
            len([row for row in admin_rows if row["api_view"] in ACCESS_VIEWS]),
        )
        self.assertEqual(
            expected_unlock,
            len([row for row in admin_rows if row["api_view"] == UNLOCK_VIEW]),
        )

    def test_planner_is_denied_everywhere(self):
        permission = self.permission_of(VIEWER_ROLE)
        requests = [
            ("get", ROLES_URL, None),
            ("post", ROLES_URL, {"name": "x"}),
            ("get", f"{ROLES_URL}3/", None),
            ("put", f"{ROLES_URL}2/", {"name": "planner2"}),
            ("delete", f"{ROLES_URL}2/", None),
            ("get", PERMISSION_URL, None),
            ("put", f"{PERMISSION_URL}{permission.id}/", {"action_id": PATCH}),
            ("delete", f"{PERMISSION_URL}{permission.id}/", None),
            ("get", ACTIONS_URL, None),
            ("get", APIVIEW_URL, None),
        ]
        for method, url, body in requests:
            with self.subTest(method=method, url=url):
                response = self.request(method, url, "cfplanner", body)
                self.assertEqual(403, response.status_code, response.json)
        self.assertEqual("planner", RoleModel.query.get(2).name)


class _AdminAllowedCases:
    """Level 1: the client admin reaches the views, the reserved range stays closed."""

    def test_admin_lists_roles(self):
        response = self.request("get", ROLES_URL, "cfadmin")
        self.assertEqual(200, response.status_code, response.json)
        ids = {row["id"] for row in response.json}
        self.assertTrue({901, 902, 903} <= ids)

    def test_admin_creates_role_without_id(self):
        expected = max(r.id for r in RoleModel.query.all() if r.id < 900) + 1
        response = self.request("post", ROLES_URL, "cfadmin", {"name": "auditor"})
        self.assertEqual(201, response.status_code, response.json)
        self.assertLess(response.json["id"], 900)
        self.assertEqual(expected, response.json["id"])
        self.assertEqual("auditor", RoleModel.query.get(expected).name)

    def test_admin_creates_role_with_id(self):
        response = self.request("post", ROLES_URL, "cfadmin", {"id": 10, "name": "r10"})
        self.assertEqual(201, response.status_code, response.json)
        self.assertEqual(10, response.json["id"])

    def test_admin_cannot_create_reserved_role(self):
        response = self.request("post", ROLES_URL, "cfadmin", {"id": 950, "name": "x"})
        self.assert_error(response, 403, RESERVED_ROLE_ERROR)
        self.assertIsNone(RoleModel.query.get(950))

    def test_admin_cannot_create_duplicated_role(self):
        response = self.request("post", ROLES_URL, "cfadmin", {"id": 3, "name": "dup"})
        self.assert_error(response, 400, "The object does exist already")
        self.assertEqual("admin", RoleModel.query.get(3).name)

    def test_admin_gets_role(self):
        self.assertEqual(200, self.request("get", f"{ROLES_URL}903/", "cfadmin").status_code)

    def test_admin_edits_role(self):
        response = self.request("put", f"{ROLES_URL}2/", "cfadmin", {"name": "planner2"})
        self.assertEqual(200, response.status_code, response.json)
        db.session.expire_all()
        self.assertEqual("planner2", RoleModel.query.get(2).name)

    def test_admin_cannot_edit_reserved_role(self):
        name = RoleModel.query.get(902).name
        response = self.request("put", f"{ROLES_URL}902/", "cfadmin", {"name": "x"})
        self.assert_error(response, 403, RESERVED_ROLE_ERROR)
        db.session.expire_all()
        self.assertEqual(name, RoleModel.query.get(902).name)

    def test_admin_cannot_move_role_into_reserved_range(self):
        created = self.request("post", ROLES_URL, "cfadmin", {"name": "auditor"})
        role_id = created.json["id"]
        response = self.request("put", f"{ROLES_URL}{role_id}/", "cfadmin", {"id": 950})
        self.assert_error(response, 403, RESERVED_ROLE_ERROR)
        db.session.expire_all()
        self.assertIsNone(RoleModel.query.get(950))
        self.assertIsNotNone(RoleModel.query.get(role_id))

    def test_admin_delete_role_is_not_implemented(self):
        response = self.request("delete", f"{ROLES_URL}2/", "cfadmin")
        self.assert_error(response, 501, "Roles can not be deleted")

    def test_admin_cannot_delete_reserved_role(self):
        response = self.request("delete", f"{ROLES_URL}903/", "cfadmin")
        self.assert_error(response, 403, RESERVED_ROLE_ERROR)

    def test_admin_lists_permissions(self):
        self.assertEqual(200, self.request("get", PERMISSION_URL, "cfadmin").status_code)

    def test_admin_creates_permission(self):
        # The viewer only has GET
        view = self.view_id("instance")
        response = self.request(
            "post", PERMISSION_URL, "cfadmin",
            {"role_id": VIEWER_ROLE, "action_id": POST, "api_view_id": view},
        )
        self.assertEqual(201, response.status_code, response.json)

    def test_admin_cannot_create_permission_of_platform_role(self):
        view = self.view_id("instance")
        before = PermissionViewRoleModel.query.count()
        response = self.request(
            "post", PERMISSION_URL, "cfadmin",
            {"role_id": 902, "action_id": DELETE, "api_view_id": view},
        )
        self.assert_error(response, 403, PLATFORM_ROLE_PERMISSION_ERROR)
        self.assertEqual(before, PermissionViewRoleModel.query.count())

    def test_admin_cannot_edit_permission_of_platform_role(self):
        permission = self.permission_of(902)
        action = permission.action_id
        response = self.request(
            "put", f"{PERMISSION_URL}{permission.id}/", "cfadmin", {"action_id": PATCH}
        )
        self.assert_error(response, 403, PLATFORM_ROLE_PERMISSION_ERROR)
        db.session.expire_all()
        self.assertEqual(action, PermissionViewRoleModel.query.get(permission.id).action_id)

    def test_admin_cannot_move_permission_to_platform_role(self):
        permission = self.permission_of(VIEWER_ROLE)
        response = self.request(
            "put", f"{PERMISSION_URL}{permission.id}/", "cfadmin", {"role_id": 901}
        )
        self.assert_error(response, 403, PLATFORM_ROLE_PERMISSION_ERROR)
        db.session.expire_all()
        self.assertEqual(VIEWER_ROLE, PermissionViewRoleModel.query.get(permission.id).role_id)

    def test_admin_edits_permission_of_client_role(self):
        permission = self.permission_of(VIEWER_ROLE, "instance")
        response = self.request(
            "put", f"{PERMISSION_URL}{permission.id}/", "cfadmin", {"action_id": PATCH}
        )
        self.assertEqual(200, response.status_code, response.json)
        db.session.expire_all()
        self.assertEqual(PATCH, PermissionViewRoleModel.query.get(permission.id).action_id)

    def test_admin_cannot_delete_permission_of_platform_role(self):
        permission = self.permission_of(PLATFORM_ADMIN_ROLE)
        response = self.request("delete", f"{PERMISSION_URL}{permission.id}/", "cfadmin")
        self.assert_error(response, 403, PLATFORM_ROLE_PERMISSION_ERROR)
        db.session.expire_all()
        self.assertIsNotNone(PermissionViewRoleModel.query.get(permission.id))

    def test_admin_deletes_permission_of_client_role(self):
        permission = self.permission_of(VIEWER_ROLE)
        response = self.request("delete", f"{PERMISSION_URL}{permission.id}/", "cfadmin")
        self.assertEqual(200, response.status_code, response.json)
        db.session.expire_all()
        self.assertIsNone(PermissionViewRoleModel.query.get(permission.id))

    def test_admin_reads_actions_and_views(self):
        self.assertEqual(200, self.request("get", ACTIONS_URL, "cfadmin").status_code)
        self.assertEqual(200, self.request("get", APIVIEW_URL, "cfadmin").status_code)

    def test_access_init_survives_role_of_admin(self):
        # The id of the new role is below the reserved range, so the next
        # start (access_init) does not stop
        self.request("post", ROLES_URL, "cfadmin", {"name": "auditor"})
        access_init_command(verbose=False)


class _AdminDeniedCases:
    """Levels 2 and 3: the table does not give the admin these views."""

    def test_admin_is_denied_by_the_table(self):
        permission = self.permission_of(VIEWER_ROLE)
        requests = [
            ("get", ROLES_URL, None),
            ("post", ROLES_URL, {"name": "auditor"}),
            ("post", ROLES_URL, {"id": 10, "name": "r10"}),
            ("post", ROLES_URL, {"id": 950, "name": "x"}),
            ("post", ROLES_URL, {"id": 3, "name": "dup"}),
            ("get", f"{ROLES_URL}903/", None),
            ("put", f"{ROLES_URL}2/", {"name": "planner2"}),
            ("put", f"{ROLES_URL}902/", {"name": "x"}),
            ("delete", f"{ROLES_URL}2/", None),
            ("delete", f"{ROLES_URL}903/", None),
            ("get", PERMISSION_URL, None),
            (
                "post",
                PERMISSION_URL,
                {"role_id": 1, "action_id": POST, "api_view_id": 1},
            ),
            ("put", f"{PERMISSION_URL}{permission.id}/", {"action_id": PATCH}),
            ("delete", f"{PERMISSION_URL}{permission.id}/", None),
            ("get", ACTIONS_URL, None),
            ("get", APIVIEW_URL, None),
        ]
        roles_before = RoleModel.query.count()
        permissions_before = self.all_permission_tuples()
        for method, url, body in requests:
            with self.subTest(method=method, url=url, body=body):
                self.assert_table_denied(self.request(method, url, "cfadmin", body))
        db.session.expire_all()
        self.assertEqual(roles_before, RoleModel.query.count())
        self.assertEqual(permissions_before, self.all_permission_tuples())
        self.assertEqual("planner", RoleModel.query.get(2).name)


class TestAccessManagementLevel1(
    _AccessManagementPlatformCases, _AdminAllowedCases, _LevelCase
):
    security_level = 1
    config_overrides = level_overrides(1)


class TestAccessManagementLevel2(
    _AccessManagementPlatformCases, _AdminDeniedCases, _LevelCase
):
    security_level = 2
    config_overrides = level_overrides(2)


class TestAccessManagementLevel3(
    _AccessManagementPlatformCases, _AdminDeniedCases, _LevelCase
):
    security_level = 3
    config_overrides = level_overrides(3)


class TestNextFreeRoleId(_LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)

    def add_role(self, role_id, soft_deleted=False):
        from datetime import datetime, timezone

        role = RoleModel({"id": role_id, "name": f"r{role_id}"})
        if soft_deleted:
            role.deleted_at = datetime.now(timezone.utc)
        role.save()

    def test_first_free_id(self):
        self.assertEqual(5, RoleModel.next_free_id_below_reserved_range())

    def test_soft_deleted_role_counts(self):
        self.add_role(7, soft_deleted=True)
        self.assertEqual(8, RoleModel.next_free_id_below_reserved_range())

    def test_role_above_the_range_does_not_count(self):
        self.add_role(1200)
        self.assertEqual(5, RoleModel.next_free_id_below_reserved_range())

    def test_no_free_id(self):
        self.add_role(899)
        self.assertIsNone(RoleModel.next_free_id_below_reserved_range())
        response = self.request("post", ROLES_URL, "cfplatform", {"name": "x"})
        self.assert_error(response, 400, NO_FREE_ROLE_ID_ERROR)

    def test_automatic_id_follows_the_highest_one(self):
        self.add_role(40)
        response = self.request("post", ROLES_URL, "cfplatform", {"name": "x"})
        self.assertEqual(201, response.status_code, response.json)
        self.assertEqual(41, response.json["id"])


# --------------------------------------------------------------------------
# E. Role assignment and revocation
# --------------------------------------------------------------------------
class _RoleAssignmentCases:
    # whether a client admin can revoke the admin role at this level
    admin_can_revoke_admin = False

    def has_role(self, user, role):
        db.session.expire_all()
        return UserRoleModel.check_if_role_assigned(user_id=user.id, role_id=role)

    def test_admin_cannot_grant_platform_role(self):
        response = self.request(
            "post", USER_ROLE_URL, "cfadmin", {"user_id": self.planner.id, "role_id": 902}
        )
        self.assertEqual(403, response.status_code, response.json)
        self.assertFalse(self.has_role(self.planner, 902))

    def test_admin_grants_admin_role(self):
        response = self.request(
            "post", USER_ROLE_URL, "cfadmin", {"user_id": self.planner.id, "role_id": ADMIN_ROLE}
        )
        self.assertEqual(201, response.status_code, response.json)
        self.assertTrue(self.has_role(self.planner, ADMIN_ROLE))

    def test_admin_revokes_admin_role_of_another_admin(self):
        response = self.request("delete", f"{USER_ROLE_URL}{self.admin2.id}/{ADMIN_ROLE}/", "cfadmin")
        if self.admin_can_revoke_admin:
            self.assertEqual(200, response.status_code, response.json)
            self.assertFalse(self.has_role(self.admin2, ADMIN_ROLE))
        else:
            self.assert_error(response, 403, REVOKE_ROLE_ERROR)
            self.assertTrue(self.has_role(self.admin2, ADMIN_ROLE))

    def test_admin_toggles_off_admin_role(self):
        response = self.request("put", f"{USER_URL}{self.admin2.id}/0/", "cfadmin")
        if self.admin_can_revoke_admin:
            self.assertEqual(200, response.status_code, response.json)
            self.assertFalse(self.has_role(self.admin2, ADMIN_ROLE))
        else:
            self.assert_error(response, 403, REVOKE_ADMIN_ERROR)
            self.assertTrue(self.has_role(self.admin2, ADMIN_ROLE))

    def test_admin_cannot_revoke_platform_role(self):
        response = self.request(
            "delete", f"{USER_ROLE_URL}{self.platform_viewer.id}/{PLATFORM_VIEWER_ROLE}/", "cfadmin"
        )
        self.assert_error(response, 403, REVOKE_ROLE_ERROR)
        self.assertTrue(self.has_role(self.platform_viewer, PLATFORM_VIEWER_ROLE))

    def test_platform_revokes_admin_role_with_delete(self):
        response = self.request(
            "delete", f"{USER_ROLE_URL}{self.admin2.id}/{ADMIN_ROLE}/", "cfplatform"
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.has_role(self.admin2, ADMIN_ROLE))

    def test_platform_revokes_admin_role_with_toggle(self):
        response = self.request("put", f"{USER_URL}{self.admin2.id}/0/", "cfplatform")
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.has_role(self.admin2, ADMIN_ROLE))

    def test_platform_revokes_platform_role(self):
        response = self.request(
            "delete", f"{USER_ROLE_URL}{self.platform_viewer.id}/{PLATFORM_VIEWER_ROLE}/", "cfplatform"
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.has_role(self.platform_viewer, PLATFORM_VIEWER_ROLE))

    def test_admin_makes_admin_with_toggle(self):
        response = self.request("put", f"{USER_URL}{self.planner.id}/1/", "cfadmin")
        self.assertEqual(200, response.status_code, response.json)
        self.assertTrue(self.has_role(self.planner, ADMIN_ROLE))

    def test_admin_revokes_unprotected_role(self):
        response = self.request(
            "delete", f"{USER_ROLE_URL}{self.planner.id}/{PLANNER_ROLE}/", "cfadmin"
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.has_role(self.planner, PLANNER_ROLE))


class TestRoleAssignmentLevel1(_RoleAssignmentCases, _LevelCase):
    security_level = 1
    config_overrides = level_overrides(1)
    admin_can_revoke_admin = True


class TestRoleAssignmentLevel2(_RoleAssignmentCases, _LevelCase):
    security_level = 2
    config_overrides = level_overrides(2)


class TestRoleAssignmentLevel3(_RoleAssignmentCases, _LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)


# --------------------------------------------------------------------------
# F. Sign up
# --------------------------------------------------------------------------
class _SignupCases:
    expected_signup_activated = None
    admin_can_sign_up = False

    def sign_up(self, username, new_user="newuser"):
        body = {"username": new_user, "email": f"{new_user}@test.org", "password": P}
        headers = JSON_HEADER if username is None else self.headers(username)
        return self.client.post(SIGNUP_URL, data=json.dumps(body), headers=headers)

    def test_signup_activated_of_the_level(self):
        self.assertEqual(self.expected_signup_activated, int(self.app.config["SIGNUP_ACTIVATED"]))

    def test_admin_signs_up_user(self):
        response = self.sign_up("cfadmin")
        if self.admin_can_sign_up:
            self.assertEqual(201, response.status_code, response.json)
            self.assertIsNotNone(self.fresh_user("newuser"))
        else:
            self.assert_error(response, 403, SIGNUP_RESTRICTED_ERROR)
            self.assertIsNone(self.fresh_user("newuser"))

    def test_platform_admin_signs_up_user(self):
        response = self.sign_up("cfplatform")
        self.assertEqual(201, response.status_code, response.json)
        self.assertIsNotNone(self.fresh_user("newuser"))

    def test_signup_without_authorization(self):
        response = self.sign_up(None)
        self.assertEqual(400, response.status_code, response.json)
        self.assertIsNone(self.fresh_user("newuser"))

    def test_planner_cannot_sign_up_users(self):
        response = self.sign_up("cfplanner")
        self.assertEqual(403, response.status_code, response.json)
        self.assertIsNone(self.fresh_user("newuser"))


class TestSignupLevel1(_SignupCases, _LevelCase):
    security_level = 1
    config_overrides = level_overrides(1)
    expected_signup_activated = 2
    admin_can_sign_up = True


class TestSignupLevel2(_SignupCases, _LevelCase):
    security_level = 2
    config_overrides = level_overrides(2)
    expected_signup_activated = 3

    def test_level_2_only_platform_admin_signs_up_users(self):
        self.assert_error(self.sign_up("cfadmin"), 403, SIGNUP_RESTRICTED_ERROR)
        self.assertIsNone(self.fresh_user("newuser"))
        self.assertEqual(201, self.sign_up("cfplatform").status_code)
        self.assertIsNotNone(self.fresh_user("newuser"))


class TestSignupLevel3(_SignupCases, _LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)
    expected_signup_activated = 3


# --------------------------------------------------------------------------
# G. Unlock
# --------------------------------------------------------------------------
class _UnlockCases:
    # whether the client admin reaches the unlock endpoint (table)
    admin_reaches_unlock = True

    def setUp(self):
        super().setUp()
        self.lock(self.planner)
        self.lock(self.platform_viewer)
        self.lock(self.admin2)

    def unlock(self, actor, user_id):
        return self.request("put", f"{USER_URL}{user_id}/unlock/", actor)

    def login_status(self, username):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": P}),
            headers=JSON_HEADER,
        ).status_code

    def assert_unlocked(self, username):
        user = self.fresh_user(username)
        self.assertFalse(user.locked)
        self.assertEqual(0, user.failed_login_attempts)

    def assert_still_locked(self, username):
        self.assertTrue(self.fresh_user(username).locked)

    def test_admin_unlocks_user_without_platform_roles(self):
        response = self.unlock("cfadmin", self.planner.id)
        if self.admin_reaches_unlock:
            self.assertEqual(200, response.status_code, response.json)
            self.assertEqual(UNLOCKED_MESSAGE, response.json["message"])
            self.assert_unlocked("cfplanner")
            self.assertEqual(200, self.login_status("cfplanner"))
        else:
            self.assert_table_denied(response)
            self.assert_still_locked("cfplanner")

    def test_admin_cannot_unlock_platform_user(self):
        response = self.unlock("cfadmin", self.platform_viewer.id)
        if self.admin_reaches_unlock:
            self.assert_error(response, 403, UNLOCK_PLATFORM_USER_ERROR)
        else:
            self.assert_table_denied(response)
        self.assert_still_locked("cfpviewer")

    def test_platform_admin_unlocks_anyone(self):
        for username, user in (("cfplanner", self.planner), ("cfpviewer", self.platform_viewer)):
            with self.subTest(username=username):
                response = self.unlock("cfplatform", user.id)
                self.assertEqual(200, response.status_code, response.json)
                self.assertEqual(UNLOCKED_MESSAGE, response.json["message"])
                self.assert_unlocked(username)

    def test_admin_unlocks_another_admin(self):
        response = self.unlock("cfadmin", self.admin2.id)
        if self.admin_reaches_unlock:
            self.assertEqual(200, response.status_code, response.json)
            self.assert_unlocked("cfadmin2")
        else:
            self.assert_table_denied(response)
            self.assert_still_locked("cfadmin2")

    def test_unlock_of_unknown_user(self):
        response = self.unlock("cfadmin", 99999)
        if self.admin_reaches_unlock:
            self.assertEqual(404, response.status_code, response.json)
        else:
            self.assert_table_denied(response)

    def test_platform_admin_unlock_of_unknown_user(self):
        self.assertEqual(404, self.unlock("cfplatform", 99999).status_code)

    def test_planner_cannot_unlock(self):
        other = self.make_user("cfother", VIEWER_ROLE)
        self.lock(other)
        # the planner itself is locked: unlock it first to be able to log in
        self.fresh_user("cfplanner").unlock_account()
        response = self.unlock("cfplanner", other.id)
        self.assertEqual(403, response.status_code, response.json)
        self.assert_still_locked("cfother")

    def test_audit_event_of_the_unlock(self):
        response = self.unlock("cfadmin", self.planner.id)
        events = self.capture.by_event("account.unlocked")
        if self.admin_reaches_unlock:
            self.assertEqual(200, response.status_code, response.json)
            self.assertEqual(1, len(events), self.capture.records)
            self.assertEqual("cfadmin", events[0]["actor"])
            self.assertEqual("cfplanner", events[0]["target"])
        else:
            self.assertEqual([], events)

    def test_no_audit_event_when_the_unlock_is_refused(self):
        self.unlock("cfadmin", self.platform_viewer.id)
        self.assertEqual([], self.capture.by_event("account.unlocked"))

    def test_cli_unlocks_user(self):
        self.run_cli_unlock("cfplanner")
        self.assert_unlocked("cfplanner")

    def test_cli_unlocks_platform_user(self):
        self.run_cli_unlock("cfpviewer")
        self.assert_unlocked("cfpviewer")

    def run_cli_unlock(self, username):
        with patch.object(
            import_module("cornflow.cli.users"), "get_app", return_value=self.app
        ):
            result = CliRunner().invoke(cli, ["users", "unlock", "-u", username])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(f"User {username} has been unlocked", result.output)


class TestUnlockLevel1(_UnlockCases, _LevelCase):
    security_level = 1
    config_overrides = level_overrides(1)


class TestUnlockLevel2(_UnlockCases, _LevelCase):
    security_level = 2
    config_overrides = level_overrides(2)


class TestUnlockLevel3(_UnlockCases, _LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)
    admin_reaches_unlock = False


# --------------------------------------------------------------------------
# H. Edit, MFA reset and delete of platform users
# --------------------------------------------------------------------------
EDIT_PLATFORM_USER_ERROR = "Only a platform administrator can edit a platform user"
MFA_RESET_PLATFORM_USER_ERROR = (
    "Only a platform administrator can reset the two-factor authentication of "
    "a platform user"
)
DELETE_PLATFORM_USER_ERROR = "Only a platform administrator can delete a platform user"
NEW_P = "Vb2#nQ8w!Lz5Tr"  # valid at the three levels


class _PlatformUserGuardCases:
    """
    A client admin passes ``is_admin()`` but must not take over, strip the
    second factor of, or delete a user with platform roles (same rule as the
    unlock endpoint). A platform administrator still can.
    """

    def enable_mfa(self, user):
        user = self.fresh_user(user.username)
        user.mfa_enabled = True
        user.save()

    def login_status(self, username, password):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": password}),
            headers=JSON_HEADER,
        ).status_code

    def test_admin_cannot_set_password_of_platform_admin(self):
        response = self.request(
            "put",
            f"{USER_URL}{self.platform_admin.id}/",
            "cfadmin",
            {"password": NEW_P},
        )
        self.assert_error(response, 403, EDIT_PLATFORM_USER_ERROR)
        self.assertTrue(self.fresh_user("cfplatform").check_hash(P))
        self.assertNotEqual(200, self.login_status("cfplatform", NEW_P))

    def test_admin_cannot_edit_platform_viewer(self):
        response = self.request(
            "put",
            f"{USER_URL}{self.platform_viewer.id}/",
            "cfadmin",
            {"email": "taken@test.org"},
        )
        self.assert_error(response, 403, EDIT_PLATFORM_USER_ERROR)
        self.assertEqual("cfpviewer@test.org", self.fresh_user("cfpviewer").email)

    def test_admin_still_edits_client_users(self):
        response = self.request(
            "put", f"{USER_URL}{self.planner.id}/", "cfadmin", {"password": NEW_P}
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertTrue(self.fresh_user("cfplanner").check_hash(NEW_P))

    def test_platform_admin_edits_platform_user(self):
        response = self.request(
            "put",
            f"{USER_URL}{self.platform_viewer.id}/",
            "cfplatform",
            {"first_name": "Edited"},
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual("Edited", self.fresh_user("cfpviewer").first_name)

    def test_platform_user_edits_themselves(self):
        response = self.request(
            "put",
            f"{USER_URL}{self.platform_viewer.id}/",
            "cfpviewer",
            {"first_name": "Self"},
        )
        self.assertEqual(200, response.status_code, response.json)

    def test_admin_cannot_reset_mfa_of_platform_admin(self):
        self.enable_mfa(self.platform_admin)
        # the client admin logs in before the platform admin has MFA in the way
        headers = self.headers("cfadmin")
        response = self.client.delete(
            f"{USER_URL}{self.platform_admin.id}/mfa/", headers=headers
        )
        self.assert_error(response, 403, MFA_RESET_PLATFORM_USER_ERROR)
        self.assertTrue(self.fresh_user("cfplatform").mfa_enabled)
        self.assertEqual([], self.capture.by_event("mfa.reset"))

    def test_admin_still_resets_mfa_of_client_users(self):
        self.enable_mfa(self.planner)
        response = self.request("delete", f"{USER_URL}{self.planner.id}/mfa/", "cfadmin")
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.fresh_user("cfplanner").mfa_enabled)

    def test_platform_admin_resets_mfa_of_platform_user(self):
        self.enable_mfa(self.platform_viewer)
        response = self.request(
            "delete", f"{USER_URL}{self.platform_viewer.id}/mfa/", "cfplatform"
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertFalse(self.fresh_user("cfpviewer").mfa_enabled)

    def test_admin_cannot_delete_platform_admin(self):
        response = self.request(
            "delete", f"{USER_URL}{self.platform_admin.id}/", "cfadmin"
        )
        self.assert_error(response, 403, DELETE_PLATFORM_USER_ERROR)
        self.assertIsNotNone(self.fresh_user("cfplatform"))

    def test_platform_admin_deletes_platform_user(self):
        response = self.request(
            "delete", f"{USER_URL}{self.platform_viewer.id}/", "cfplatform"
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertIsNone(self.fresh_user("cfpviewer"))


class TestPlatformUserGuardLevel1(_PlatformUserGuardCases, _LevelCase):
    security_level = 1
    config_overrides = level_overrides(1)


class TestPlatformUserGuardLevel2(_PlatformUserGuardCases, _LevelCase):
    security_level = 2
    config_overrides = level_overrides(2)


class TestPlatformUserGuardLevel3(_PlatformUserGuardCases, _LevelCase):
    security_level = 3
    config_overrides = level_overrides(3)


if __name__ == "__main__":
    unittest.main()
