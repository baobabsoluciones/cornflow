"""
Tests for the personal API key lifecycle:

- read-only ("read") vs full scope,
- the rotation grace window (generate first, redeploy after),
- the expiry notifications (threshold logic, recipients, idempotency).
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask import current_app
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.commands.token_expiry import (
    get_notification_thresholds,
    get_platform_admin_emails,
    get_threshold_to_notify,
    notify_api_key_expiry,
)
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    API_KEY_SCOPE_FULL,
    API_KEY_SCOPE_READ,
    PLATFORM_ADMIN_ROLE,
)
from cornflow.tests.const import INSTANCE_PATH, INSTANCE_URL, LOGIN_URL, SIGNUP_URL

STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
JSON_HEADER = {"Content-Type": "application/json"}
API_KEY_URL = "/user/api-key/"


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


def load_file(path):
    with open(path) as handler:
        return json.load(handler)


class ApiKeyTestBase(TestCase):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
        self.payload = load_file(INSTANCE_PATH)
        self.data = {
            "username": "keyuser",
            "email": "keyuser@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {
                    "username": self.data["username"],
                    "password": self.data["password"],
                }
            ),
            headers=JSON_HEADER,
        ).json["token"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def mint_key(self, scope=None):
        body = {} if scope is None else {"scope": scope}
        response = self.client.post(
            API_KEY_URL, data=json.dumps(body), headers=auth_header(self.token)
        )
        self.assertEqual(201, response.status_code)
        return response.json

    def user(self):
        db.session.expire_all()
        return UserModel.get_one_user(self.user_id)


class TestApiKeyScope(ApiKeyTestBase):
    def test_full_scope_by_default(self):
        result = self.mint_key()
        self.assertEqual(API_KEY_SCOPE_FULL, result["scope"])
        self.assertEqual(API_KEY_SCOPE_FULL, self.user().api_key_scope)
        # a full key can read and write
        key = result["api_key"]
        self.assertEqual(
            200, self.client.get(INSTANCE_URL, headers=auth_header(key)).status_code
        )
        self.assertEqual(
            201,
            self.client.post(
                INSTANCE_URL,
                data=json.dumps(self.payload),
                headers=auth_header(key),
            ).status_code,
        )

    def test_read_only_key_can_read(self):
        key = self.mint_key(scope=API_KEY_SCOPE_READ)["api_key"]
        response = self.client.get(INSTANCE_URL, headers=auth_header(key))
        self.assertEqual(200, response.status_code)

    def test_read_only_key_can_not_write(self):
        key = self.mint_key(scope=API_KEY_SCOPE_READ)["api_key"]
        response = self.client.post(
            INSTANCE_URL, data=json.dumps(self.payload), headers=auth_header(key)
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_read_only", response.json.get("error_code"))

    def test_read_only_key_can_not_delete_or_put(self):
        # create an instance with the session first
        instance_id = self.client.post(
            INSTANCE_URL,
            data=json.dumps(self.payload),
            headers=auth_header(self.token),
        ).json["id"]
        key = self.mint_key(scope=API_KEY_SCOPE_READ)["api_key"]
        detail = f"{INSTANCE_URL}{instance_id}/"
        self.assertEqual(
            403,
            self.client.put(
                detail, data=json.dumps({"name": "x"}), headers=auth_header(key)
            ).status_code,
        )
        self.assertEqual(
            403, self.client.delete(detail, headers=auth_header(key)).status_code
        )
        # but reading it is fine
        self.assertEqual(
            200, self.client.get(detail, headers=auth_header(key)).status_code
        )

    def test_scope_is_recorded_and_reported(self):
        result = self.mint_key(scope=API_KEY_SCOPE_READ)
        self.assertEqual(API_KEY_SCOPE_READ, result["scope"])
        self.assertEqual(API_KEY_SCOPE_READ, self.user().api_key_scope)

    def test_invalid_scope_is_rejected(self):
        response = self.client.post(
            API_KEY_URL,
            data=json.dumps({"scope": "superuser"}),
            headers=auth_header(self.token),
        )
        self.assertEqual(400, response.status_code)


class TestApiKeyRotationGrace(ApiKeyTestBase):
    def test_previous_key_survives_the_grace_window(self):
        first = self.mint_key()["api_key"]
        self.assertEqual(
            200, self.client.get(INSTANCE_URL, headers=auth_header(first)).status_code
        )
        second = self.mint_key()["api_key"]
        # the new key works...
        self.assertEqual(
            200, self.client.get(INSTANCE_URL, headers=auth_header(second)).status_code
        )
        # ...and so does the previous one, inside the grace window
        self.assertEqual(
            200, self.client.get(INSTANCE_URL, headers=auth_header(first)).status_code
        )

    def test_previous_key_dies_after_the_grace_window(self):
        first = self.mint_key()["api_key"]
        self.mint_key()
        # move the grace deadline into the past
        user = self.user()
        user.api_key_grace_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.add(user)
        db.session.commit()
        response = self.client.get(INSTANCE_URL, headers=auth_header(first))
        self.assertEqual(401, response.status_code)

    def test_grace_disabled_kills_the_previous_key_at_once(self):
        current_app.config["API_KEY_ROTATION_GRACE_MINUTES"] = 0
        try:
            first = self.mint_key()["api_key"]
            self.mint_key()
            response = self.client.get(INSTANCE_URL, headers=auth_header(first))
            self.assertEqual(401, response.status_code)
        finally:
            current_app.config["API_KEY_ROTATION_GRACE_MINUTES"] = 60

    def test_explicit_revocation_ignores_the_grace(self):
        first = self.mint_key()["api_key"]
        response = self.client.delete(API_KEY_URL, headers=auth_header(self.token))
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            401, self.client.get(INSTANCE_URL, headers=auth_header(first)).status_code
        )
        # and the metadata is cleared
        self.assertIsNone(self.user().api_key_issued_at)
        self.assertIsNone(self.user().api_key_grace_until)

    def test_older_keys_are_not_covered_by_the_grace(self):
        # only the immediately superseded key gets the grace
        oldest = self.mint_key()["api_key"]
        self.mint_key()
        self.mint_key()
        response = self.client.get(INSTANCE_URL, headers=auth_header(oldest))
        self.assertEqual(401, response.status_code)


class TestApiKeyExpiryThresholds(TestCase):
    """Pure threshold logic: no database needed."""

    def create_app(self):
        return create_app("testing")

    def test_configured_thresholds(self):
        self.assertEqual([30, 7, 3, 2, 1], get_notification_thresholds())

    def test_invalid_entries_are_ignored(self):
        current_app.config["TOKEN_EXPIRY_NOTIFICATION_DAYS"] = "30, nonsense, 7,,3"
        try:
            self.assertEqual([30, 7, 3], get_notification_thresholds())
        finally:
            current_app.config["TOKEN_EXPIRY_NOTIFICATION_DAYS"] = "30,7,3,2,1"

    def test_nothing_to_send_when_far_from_expiry(self):
        self.assertIsNone(get_threshold_to_notify(45, None, [30, 7, 3, 2, 1]))

    def test_first_notice_when_crossing_the_largest_threshold(self):
        self.assertEqual(30, get_threshold_to_notify(30, None, [30, 7, 3, 2, 1]))
        # a run that lands below the threshold still notifies (no equality)
        self.assertEqual(30, get_threshold_to_notify(29, None, [30, 7, 3, 2, 1]))

    def test_missed_runs_are_caught_up_with_a_single_notice(self):
        # the job did not run for a week: the next run notifies once and marks
        # every threshold it skipped as covered
        self.assertEqual(7, get_threshold_to_notify(5, 30, [30, 7, 3, 2, 1]))

    def test_no_duplicate_for_an_already_notified_threshold(self):
        self.assertIsNone(get_threshold_to_notify(5, 7, [30, 7, 3, 2, 1]))
        self.assertIsNone(get_threshold_to_notify(2, 2, [30, 7, 3, 2, 1]))

    def test_running_twice_the_same_day_sends_once(self):
        # first run of the day at 1 day left records the smallest threshold...
        threshold = get_threshold_to_notify(1, None, [30, 7, 3, 2, 1])
        self.assertEqual(1, threshold)
        # ...so a second run the same day has nothing to send
        self.assertIsNone(get_threshold_to_notify(1, threshold, [30, 7, 3, 2, 1]))

    def test_expired_key_stops_notifying(self):
        self.assertIsNone(get_threshold_to_notify(-3, 1, [30, 7, 3, 2, 1]))


class TestApiKeyExpiryNotification(ApiKeyTestBase):
    def setUp(self):
        super().setUp()
        # a platform administrator, always warned about expiring keys
        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": "platformadmin",
                    "email": "platformadmin@test.com",
                    "password": "Nw5@rT8y!Kd3Zx",
                }
            ),
            headers=JSON_HEADER,
        )
        UserRoleModel(
            {"user_id": response.json["id"], "role_id": PLATFORM_ADMIN_ROLE}
        ).save()
        # the testing config has no SMTP settings: provide them so the
        # notification path builds and "sends" the emails (send_email_to is
        # patched in every test)
        current_app.config["SERVICE_EMAIL_ADDRESS"] = "cornflow@test.com"
        current_app.config["SERVICE_EMAIL_PASSWORD"] = "irrelevant"
        current_app.config["SERVICE_EMAIL_SERVER"] = "smtp.test.com"
        current_app.config["SERVICE_EMAIL_PORT"] = 465

    def age_key(self, days_left):
        """
        Backdates the key so it has `days_left` whole days left. The extra
        minute absorbs the time elapsed since `now` was read, so the whole-day
        flooring lands on the intended value instead of one day below.
        """
        user = self.user()
        duration = int(current_app.config["API_KEY_DURATION_DAYS"])
        user.api_key_issued_at = (
            datetime.now(timezone.utc)
            - timedelta(days=duration - days_left)
            + timedelta(minutes=1)
        )
        db.session.add(user)
        db.session.commit()

    def test_platform_admin_emails_are_collected(self):
        self.assertIn("platformadmin@test.com", get_platform_admin_emails())

    def test_no_notification_far_from_expiry(self):
        self.mint_key()
        with patch("cornflow.commands.token_expiry.send_email_to") as send:
            self.assertEqual(0, notify_api_key_expiry())
        send.assert_not_called()

    def test_notification_goes_to_owner_and_platform_admins(self):
        self.mint_key()
        self.age_key(days_left=29)
        with patch("cornflow.commands.token_expiry.send_email_to") as send:
            self.assertEqual(1, notify_api_key_expiry())
        receivers = {call.kwargs["receiver"] for call in send.call_args_list}
        self.assertIn("keyuser@test.com", receivers)
        self.assertIn("platformadmin@test.com", receivers)
        # and the threshold was recorded
        self.assertEqual(30, self.user().api_key_expiry_notified)

    def test_notification_is_idempotent(self):
        self.mint_key()
        self.age_key(days_left=29)
        with patch("cornflow.commands.token_expiry.send_email_to"):
            self.assertEqual(1, notify_api_key_expiry())
        # a second run the same day sends nothing
        with patch("cornflow.commands.token_expiry.send_email_to") as send:
            self.assertEqual(0, notify_api_key_expiry())
        send.assert_not_called()

    def test_next_threshold_notifies_again(self):
        self.mint_key()
        self.age_key(days_left=29)
        with patch("cornflow.commands.token_expiry.send_email_to"):
            notify_api_key_expiry()
        self.age_key(days_left=2)
        with patch("cornflow.commands.token_expiry.send_email_to") as send:
            self.assertEqual(1, notify_api_key_expiry())
        self.assertTrue(send.called)
        self.assertEqual(2, self.user().api_key_expiry_notified)

    def test_regenerating_resets_the_notifications(self):
        self.mint_key()
        self.age_key(days_left=2)
        with patch("cornflow.commands.token_expiry.send_email_to"):
            notify_api_key_expiry()
        self.assertEqual(2, self.user().api_key_expiry_notified)
        # a fresh key starts over
        self.mint_key()
        self.assertIsNone(self.user().api_key_expiry_notified)

    def test_users_without_a_key_are_skipped(self):
        # nobody minted a key: nothing to notify even at any age
        with patch("cornflow.commands.token_expiry.send_email_to") as send:
            self.assertEqual(0, notify_api_key_expiry())
        send.assert_not_called()

    def test_feature_can_be_disabled(self):
        self.mint_key()
        self.age_key(days_left=1)
        current_app.config["TOKEN_EXPIRY_NOTIFICATIONS_ENABLED"] = 0
        try:
            with patch("cornflow.commands.token_expiry.send_email_to") as send:
                self.assertEqual(0, notify_api_key_expiry())
            send.assert_not_called()
        finally:
            current_app.config["TOKEN_EXPIRY_NOTIFICATIONS_ENABLED"] = 1

    def test_expiry_metadata_is_exposed_on_the_model(self):
        self.mint_key()
        user = self.user()
        self.assertIsNotNone(user.api_key_expires_at())
        duration = int(current_app.config["API_KEY_DURATION_DAYS"])
        # a freshly minted key has (duration - 1) or duration whole days left
        self.assertIn(user.api_key_days_left(), (duration - 1, duration))
