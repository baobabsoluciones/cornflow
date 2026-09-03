"""
Tests for the separation between internal (platform) and external (client)
users:

- data isolation: instances created by a platform user are invisible to client
  users, including client admins;
- service accounts never take over the ownership of an object they update on
  behalf of a user (airflow writing back a solution, checks or KPIs);
- the guard protecting the reserved role-id range.
"""

import json

import pyotp

from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.auxiliar import check_reserved_role_ids
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import ExecutionModel, InstanceModel, RoleModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_PLANNER_ROLE,
    PLATFORM_VIEWER_ROLE,
    SERVICE_ROLE,
)
from cornflow.shared.exceptions import ConfigurationError
from cornflow.tests.const import (
    INSTANCE_PATH,
    INSTANCE_URL,
    LOGIN_URL,
    SIGNUP_URL,
    USER_ROLE_URL,
)

STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
JSON_HEADER = {"Content-Type": "application/json"}


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


def load_file(path):
    with open(path) as handler:
        return json.load(handler)


class _RoleUserMixin:
    """Creates users holding exactly one role."""

    def user_with_role(self, username, email, role_id):
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": username,
                    "email": email,
                    "password": STRONG_PASSWORD,
                }
            ),
            headers=JSON_HEADER,
        )
        user_id = response.json["id"]
        # signup assigns the default role: keep only the role under test
        UserRoleModel.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        UserRoleModel({"user_id": user_id, "role_id": role_id}).save()
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": STRONG_PASSWORD}),
            headers=JSON_HEADER,
        ).json["token"]
        return token, user_id


class TestPlatformDataIsolation(TestCase, _RoleUserMixin):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.payload = load_file(INSTANCE_PATH)
        self.client_token, self.client_id = self.user_with_role(
            "clientplanner", "clientplanner@test.com", PLANNER_ROLE
        )
        self.admin_token, _ = self.user_with_role(
            "clientadmin", "clientadmin@test.com", ADMIN_ROLE
        )
        self.platform_token, self.platform_id = self.user_with_role(
            "platformplanner", "platformplanner@test.com", PLATFORM_PLANNER_ROLE
        )
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_instance(self, token):
        response = self.client.post(
            INSTANCE_URL, data=json.dumps(self.payload), headers=auth_header(token)
        )
        self.assertEqual(201, response.status_code)
        return response.json["id"]

    def list_instances(self, token):
        response = self.client.get(INSTANCE_URL, headers=auth_header(token))
        self.assertEqual(200, response.status_code)
        return [item["id"] for item in response.json]

    def test_client_user_does_not_list_platform_instances(self):
        platform_instance = self.create_instance(self.platform_token)
        own_instance = self.create_instance(self.client_token)

        visible = self.list_instances(self.client_token)
        self.assertIn(own_instance, visible)
        self.assertNotIn(platform_instance, visible)

    def test_client_admin_does_not_list_platform_instances(self):
        # a client admin sees every object of the deployment... except those
        # belonging to the platform side
        platform_instance = self.create_instance(self.platform_token)
        client_instance = self.create_instance(self.client_token)

        visible = self.list_instances(self.admin_token)
        self.assertIn(client_instance, visible)
        self.assertNotIn(platform_instance, visible)

    def test_client_user_can_not_fetch_a_platform_instance_by_id(self):
        platform_instance = self.create_instance(self.platform_token)
        for token in (self.client_token, self.admin_token):
            response = self.client.get(
                f"{INSTANCE_URL}{platform_instance}/", headers=auth_header(token)
            )
            self.assertEqual(404, response.status_code)

    def test_platform_admin_sees_both_sides(self):
        # the platform side is the operator: its visibility is not restricted
        # by the isolation filter (a platform admin sees every object, like a
        # client admin does for the client side)
        platform_admin_token, _ = self.user_with_role(
            "platformadmin", "platformadmin@test.com", PLATFORM_ADMIN_ROLE
        )
        client_instance = self.create_instance(self.client_token)
        platform_instance = self.create_instance(self.platform_token)

        visible = self.list_instances(platform_admin_token)
        self.assertIn(platform_instance, visible)
        self.assertIn(client_instance, visible)

    def test_platform_planner_keeps_per_user_visibility(self):
        # the isolation filter does not widen anybody's visibility: a platform
        # planner is a regular (non-admin) user and still sees only its own
        # objects
        client_instance = self.create_instance(self.client_token)
        own_instance = self.create_instance(self.platform_token)

        visible = self.list_instances(self.platform_token)
        self.assertIn(own_instance, visible)
        self.assertNotIn(client_instance, visible)

    def make_execution(self, token, owner_id):
        """Creates an execution owned by `owner_id` over a new instance."""
        instance_id = self.create_instance(token)
        execution = ExecutionModel(
            {
                "user_id": owner_id,
                "instance_id": instance_id,
                "name": "platform execution",
                "description": "",
                "schema": "solve_model_dag",
                "config": {"solver": "cbc"},
            }
        )
        execution.save()
        return execution.id

    def list_executions(self, token):
        response = self.client.get("/execution/", headers=auth_header(token))
        self.assertEqual(200, response.status_code)
        return [item["id"] for item in response.json]

    def test_client_admin_does_not_list_platform_executions(self):
        # UAT 7.12: the executions list is built by ExecutionModel with its own
        # query, so it has to apply the same isolation as the detail view —
        # otherwise the object shows up in the list and 404s when opened
        platform_execution = self.make_execution(
            self.platform_token, self.platform_id
        )
        client_execution = self.make_execution(self.client_token, self.client_id)

        visible = self.list_executions(self.admin_token)
        self.assertIn(client_execution, visible)
        self.assertNotIn(platform_execution, visible)

    def test_client_user_does_not_list_platform_executions(self):
        platform_execution = self.make_execution(
            self.platform_token, self.platform_id
        )
        own_execution = self.make_execution(self.client_token, self.client_id)

        visible = self.list_executions(self.client_token)
        self.assertIn(own_execution, visible)
        self.assertNotIn(platform_execution, visible)

    def test_the_execution_list_and_detail_agree(self):
        # the two paths must never disagree: whatever the list hides, the
        # detail must refuse, and the other way round
        platform_execution = self.make_execution(
            self.platform_token, self.platform_id
        )
        self.assertNotIn(
            platform_execution, self.list_executions(self.admin_token)
        )
        detail = self.client.get(
            f"/execution/{platform_execution}/",
            headers=auth_header(self.admin_token),
        )
        self.assertEqual(404, detail.status_code)

    def test_platform_admin_lists_platform_executions(self):
        platform_admin_token, _ = self.user_with_role(
            "padminexec", "padminexec@test.com", PLATFORM_ADMIN_ROLE
        )
        platform_execution = self.make_execution(
            self.platform_token, self.platform_id
        )
        self.assertIn(
            platform_execution, self.list_executions(platform_admin_token)
        )

    def test_service_account_sees_platform_data(self):
        # UAT 12.1: airflow (a client-side service account) must read the
        # instance of a platform user to solve their execution; the isolation
        # must not apply to service accounts, which act on behalf of everyone
        service_token, _ = self.user_with_role(
            "svcisolation", "svcisolation@test.com", SERVICE_ROLE
        )
        platform_instance = self.create_instance(self.platform_token)
        response = self.client.get(
            f"{INSTANCE_URL}{platform_instance}/",
            headers=auth_header(service_token),
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(platform_instance, self.list_instances(service_token))

    def test_isolation_can_be_disabled(self):
        platform_instance = self.create_instance(self.platform_token)
        current_app.config["PLATFORM_DATA_ISOLATION"] = 0
        try:
            self.assertIn(platform_instance, self.list_instances(self.admin_token))
        finally:
            current_app.config["PLATFORM_DATA_ISOLATION"] = 1

    def test_every_platform_role_counts_as_platform(self):
        # all three platform roles put a user on the platform side (so their
        # own data is hidden from clients and they are exempt from the filter)
        for name, role_id in (
            ("pviewer", PLATFORM_VIEWER_ROLE),
            ("pplanner2", PLATFORM_PLANNER_ROLE),
            ("padmin2", PLATFORM_ADMIN_ROLE),
        ):
            _, user_id = self.user_with_role(name, f"{name}@test.com", role_id)
            self.assertTrue(
                UserRoleModel.is_platform_user(user_id),
                msg=f"{name} should be a platform user",
            )
        # ...while a client user is not
        self.assertFalse(UserRoleModel.is_platform_user(self.client_id))


class TestServiceUserAttribution(TestCase, _RoleUserMixin):
    """
    A service account acts on behalf of a user: updating an object must never
    move its ownership to the service account (which would also hide the
    object from its owner under per-user visibility).
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.payload = load_file(INSTANCE_PATH)
        self.owner_token, self.owner_id = self.user_with_role(
            "owneruser", "owneruser@test.com", PLANNER_ROLE
        )
        self.service_token, self.service_id = self.user_with_role(
            "serviceuser", "serviceuser@test.com", SERVICE_ROLE
        )
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_instance(self):
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(self.payload),
            headers=auth_header(self.owner_token),
        )
        self.assertEqual(201, response.status_code)
        return response.json["id"]

    def test_service_write_keeps_the_instance_owner(self):
        instance_id = self.create_instance()
        self.assertEqual(
            self.owner_id, InstanceModel.get_one_object(idx=instance_id).user_id
        )

        # airflow (service account) writes the instance checks back
        response = self.client.put(
            f"/dag/instance/{instance_id}/",
            data=json.dumps({"checks": {}}),
            headers=auth_header(self.service_token),
        )
        self.assertEqual(200, response.status_code)

        # the ownership did not move to the service account
        self.assertEqual(
            self.owner_id, InstanceModel.get_one_object(idx=instance_id).user_id
        )

    def test_owner_still_sees_the_instance_after_a_service_write(self):
        instance_id = self.create_instance()
        self.client.put(
            f"/dag/instance/{instance_id}/",
            data=json.dumps({"checks": {}}),
            headers=auth_header(self.service_token),
        )
        response = self.client.get(
            f"{INSTANCE_URL}{instance_id}/", headers=auth_header(self.owner_token)
        )
        self.assertEqual(200, response.status_code)


class TestReservedRoleIds(TestCase):
    """
    Tests the guard protecting the range reserved for the platform roles from
    the custom roles of external applications.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_custom_role_in_reserved_range_is_rejected(self):
        with self.assertRaises(ConfigurationError) as ctx:
            check_reserved_role_ids([PLANNER_ROLE, 950])
        self.assertIn("950", str(ctx.exception))

    def test_custom_roles_below_the_range_are_accepted(self):
        # the ids an external app conventionally uses
        check_reserved_role_ids([5, 6, 7, 799, 888, 10000])

    def test_platform_roles_are_accepted(self):
        check_reserved_role_ids(
            [PLATFORM_ADMIN_ROLE, PLATFORM_VIEWER_ROLE, PLATFORM_PLANNER_ROLE]
        )

    def test_foreign_role_stored_on_a_reserved_id_is_rejected(self):
        # a deployment whose custom role already sits inside the reserved
        # range: the upgrade must abort instead of reassigning its meaning
        RoleModel({"id": 950, "name": "supervisor"}).save()
        with self.assertRaises(ConfigurationError) as ctx:
            check_reserved_role_ids([PLANNER_ROLE])
        message = str(ctx.exception)
        self.assertIn("supervisor", message)
        self.assertIn("950", message)


class TestPlatformRoleStepUp(TestCase, _RoleUserMixin):
    """
    Granting a platform role through the API requires a fresh TOTP code from
    the acting administrator (when they have MFA enrolled): a stolen session
    token alone must not be able to mint internal accounts.
    """

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.admin_token, self.admin_id = self.user_with_role(
            "stepupadmin", "stepupadmin@test.com", PLATFORM_ADMIN_ROLE
        )
        _, self.target_id = self.user_with_role(
            "stepuptarget", "stepuptarget@test.com", PLANNER_ROLE
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def grant(self, role_id, totp_code=None):
        payload = {"user_id": self.target_id, "role_id": role_id}
        if totp_code is not None:
            payload["totp_code"] = totp_code
        return self.client.post(
            USER_ROLE_URL,
            data=json.dumps(payload),
            headers=auth_header(self.admin_token),
        )

    def enable_mfa(self):
        secret = pyotp.random_base32()
        from cornflow.models import UserModel

        user = UserModel.get_one_user(self.admin_id)
        user.set_totp_secret(secret)
        user.mfa_enabled = True
        user.save()
        return secret

    def test_without_mfa_no_step_up_applies(self):
        response = self.grant(PLATFORM_VIEWER_ROLE)
        self.assertEqual(201, response.status_code)

    def test_with_mfa_a_code_is_required(self):
        self.enable_mfa()
        response = self.grant(PLATFORM_VIEWER_ROLE)
        self.assertEqual(400, response.status_code)

    def test_with_mfa_a_wrong_code_is_rejected(self):
        self.enable_mfa()
        response = self.grant(PLATFORM_VIEWER_ROLE, totp_code="000000")
        self.assertEqual(400, response.status_code)

    def test_with_mfa_a_valid_code_grants(self):
        secret = self.enable_mfa()
        response = self.grant(
            PLATFORM_VIEWER_ROLE, totp_code=pyotp.TOTP(secret).now()
        )
        self.assertEqual(201, response.status_code)

    def test_client_roles_need_no_step_up(self):
        # the step-up protects the platform side only: ordinary role grants
        # keep working without a code even with MFA enabled
        self.enable_mfa()
        response = self.grant(ADMIN_ROLE)
        self.assertEqual(201, response.status_code)
