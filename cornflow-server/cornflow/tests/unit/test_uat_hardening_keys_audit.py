"""
UAT battery of the security hardening, group C: API keys (block 8), audit
log (block 10), HTTP headers / CORS / docs (block 11) and functional
regression (block 12).

One test per case of the UAT sheet, named after its id (``test_uat_8_4_...``
covers case 8.4). Run it in both profiles with ``CORNFLOW_UAT_PROFILE``.
"""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from importlib import import_module
from unittest.mock import Mock, patch
from urllib.parse import urlparse

from click.testing import CliRunner
from flask import current_app
from freezegun import freeze_time

from cornflow.cli import cli
from cornflow.models import PermissionsDAG, UserModel
from cornflow.shared import db
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_PLANNER_ROLE,
    SERVICE_ROLE,
    VIEWER_ROLE,
)
from cornflow.tests.const import (
    CASE_INSTANCE_URL,
    CASE_URL,
    DEPLOYED_DAG_URL,
    EXECUTION_PATH,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    HEALTH_URL,
    INSTANCE_PATH,
    INSTANCE_URL,
    LOGIN_URL,
    PREFIX,
    SCHEMA_URL,
    USER_ROLE_URL,
    USER_URL,
)
from cornflow.tests.uat_hardening_support import (
    SETTINGS,
    UatTestCase,
    auth_header,
    is_relaxed,
    is_strict,
    pending_fix,
    ui_only,
)

API_KEY_URL = PREFIX + "/user/api-key/"
DAG_URL = PREFIX + "/dag/"
REFRESH_URL = PREFIX + "/token/refresh/"
LOGOUT_URL = PREFIX + "/logout/"
NEW_PASSWORD = "Hy6-qWz.Pn4Kd8"
REVOKED_MESSAGE = "The API key has been revoked, please generate a new one"

ACCESS_RST = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "docs",
        "source",
        "deploy",
        "access.rst",
    )
)


def load_json(path):
    with open(path) as handler:
        return json.load(handler)


class AuditCapture(logging.Handler):
    """Collects the JSON records emitted on the ``cornflow.audit`` logger."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.records = []

    def emit(self, record):
        try:
            self.records.append(json.loads(record.getMessage()))
        except (ValueError, TypeError):
            pass

    def by_event(self, event):
        return [r for r in self.records if r.get("event") == event]


@contextmanager
def capture_audit():
    handler = AuditCapture()
    logger = logging.getLogger("cornflow.audit")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


class FlaskRequests:
    """
    Stand-in for the ``requests`` module used by cornflow-client: routes the
    calls to the Flask test client of the running application.
    """

    class Response:
        def __init__(self, response):
            self._response = response
            self.status_code = response.status_code
            self.text = response.get_data(as_text=True)

        def json(self):
            return self._response.get_json()

    def __init__(self, client):
        self.client = client

    def request(self, method, url, headers=None, json=None, data=None, params=None, **kwargs):
        parsed = urlparse(url)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        headers = {
            key: value
            for key, value in (headers or {}).items()
            if key.lower() != "content-encoding"
        }
        if json is not None:
            import json as json_module

            data = json_module.dumps(json)
            headers["Content-Type"] = "application/json"
        response = self.client.open(
            path,
            method=method.upper(),
            data=data,
            headers=headers,
            query_string=params,
        )
        return self.Response(response)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


def airflow_mock():
    """Replaces the Airflow client used by the execution endpoint."""
    patcher = patch("cornflow.endpoints.execution.Airflow")
    airflow_class = patcher.start()
    client = Mock()
    client.is_alive.return_value = True
    info = Mock()
    info.json.return_value = {"is_paused": False}
    client.get_workflow_info.return_value = info
    run = Mock()
    run.json.return_value = {"dag_run_id": "12345"}
    client.run_workflow.return_value = run
    airflow_class.from_config.return_value = client
    return patcher


class CommonSetup(UatTestCase):
    """Users shared by the cases of this group and a few helpers."""

    def setUp(self):
        super().setUp()
        self.planner = self.make_user("cfplanner", [PLANNER_ROLE])
        self.platform = self.make_user(
            "cfplatform", [PLATFORM_ADMIN_ROLE], email="cfplatform@example.com"
        )

    # Helpers

    def user_row(self, username):
        db.session.expire_all()
        return UserModel.get_one_user_by_username(username)

    def mint(self, username="cfplanner", scope=None, totp=True, expected=201):
        """Generates an API key through the endpoint (TOTP step-up when enrolled)."""
        token = self.token_of(username)
        body = {}
        if scope is not None:
            body["scope"] = scope
        if totp and username in self.mfa_secrets:
            body["totp_code"] = self.totp_now(username)
        response = self.client.post(
            API_KEY_URL, data=json.dumps(body), headers=auth_header(token)
        )
        self.assertEqual(expected, response.status_code, response.json)
        return response

    def key_of(self, username="cfplanner", scope=None):
        return self.mint(username, scope=scope).json["api_key"]

    def get_instances(self, key):
        return self.client.get(INSTANCE_URL, headers=auth_header(key))

    def run_cli(self, *args):
        """Runs a cornflow CLI command against the application under test."""
        app = current_app._get_current_object()
        with patch.object(
            import_module("cornflow.cli.users"), "get_app", lambda: app
        ), patch.object(import_module("cornflow.cli.tokens"), "get_app", lambda: app):
            result = CliRunner().invoke(cli, list(args))
        db.session.expire_all()
        return result

    def age_key(self, username, days_left):
        """Backdates the key so that it has ``days_left`` whole days left."""
        user = self.user_row(username)
        duration = int(current_app.config["API_KEY_DURATION_DAYS"])
        user.api_key_issued_at = (
            datetime.now(timezone.utc)
            - timedelta(days=duration - days_left)
            + timedelta(minutes=1)
        )
        db.session.add(user)
        db.session.commit()

    def enroll_if_relaxed(self, username):
        """In the relaxed profile MFA is not forced: enrol the user on purpose."""
        if is_relaxed() and username not in self.mfa_secrets:
            token = self.login(username).json["token"]
            self.enroll_mfa(token, username)


# ---------------------------------------------------------------------------
# Block 8: API keys
# ---------------------------------------------------------------------------


class TestUatApiKeys(CommonSetup):
    def test_uat_8_1_generate_key_with_mfa_without_totp(self):
        """8.1 Generate a key with MFA active, without a TOTP code."""
        self.enroll_if_relaxed("cfplanner")
        if is_strict():
            self.token_of("cfplanner")  # enrols the user
        token = self.token_of("cfplanner")
        self.assertTrue(self.user_row("cfplanner").mfa_enabled)
        response = self.client.post(
            API_KEY_URL, data=json.dumps({}), headers=auth_header(token)
        )
        if is_strict():
            self.assertEqual(SETTINGS["API_KEY_STEPUP_TOTP"], 1)
            self.assertNotIn(response.status_code, (200, 201))
            self.assertIn("two-factor", response.json["error"])
            self.assertNotIn("api_key", response.json)
            self.assertIsNone(self.user_row("cfplanner").api_key_issued_at)
        else:
            # Relaxed: the step-up is off, so even a user with MFA enrolled
            # gets the key without a code (the code only checks the flag)
            self.assertEqual(SETTINGS["API_KEY_STEPUP_TOTP"], 0)
            self.assertEqual(201, response.status_code, response.json)

    def test_uat_8_2_generate_key_with_valid_totp(self):
        """8.2 Generate a key with a valid TOTP: 201, shown only once."""
        self.enroll_if_relaxed("cfplanner")
        response = self.mint("cfplanner")
        key = response.json["api_key"]
        self.assertTrue(key)
        self.assertIn("expires_at", response.json)
        # the key is not stored anywhere: only metadata is kept on the user
        user = self.user_row("cfplanner")
        for column in user.__table__.columns:
            self.assertNotEqual(key, getattr(user, column.name))
        # a new request cannot give it back, it just rotates to another key
        second = self.mint("cfplanner").json["api_key"]
        self.assertNotEqual(key, second)

    def test_uat_8_3_use_key_on_get_instance(self):
        """8.3 Use the key on GET /instance/: 200."""
        key = self.key_of()
        self.assertEqual(200, self.get_instances(key).status_code)

    def test_uat_8_4_key_on_user_put_is_forbidden(self):
        """8.4 Use the key on PUT /user/<id>/: 403 api_key_forbidden."""
        key = self.key_of()
        response = self.client.put(
            f"{USER_URL}{self.planner.id}/",
            data=json.dumps(
                {"password": NEW_PASSWORD, "current_password": self.password_of("cfplanner")}
            ),
            headers=auth_header(key),
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_forbidden", response.json["error_code"])
        self.assertIn("interactive session", response.json["error"])

    def test_uat_8_5_key_cannot_generate_a_key(self):
        """8.5 Try to generate a key using a key: 403."""
        key = self.key_of()
        response = self.client.post(
            API_KEY_URL, data=json.dumps({}), headers=auth_header(key)
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_forbidden", response.json["error_code"])

    def test_uat_8_6_read_only_key_reports_scope(self):
        """8.6 Generate a read-only key: 201 with scope read."""
        response = self.mint("cfplanner", scope="read")
        self.assertEqual("read", response.json["scope"])
        self.assertEqual("read", self.user_row("cfplanner").api_key_scope)

    def test_uat_8_7_read_only_key_can_get(self):
        """8.7 With the read-only key: GET /instance/ is 200."""
        key = self.key_of(scope="read")
        self.assertEqual(200, self.get_instances(key).status_code)

    def test_uat_8_8_read_only_key_cannot_write(self):
        """8.8 With the read-only key: POST /instance/, PUT, DELETE are 403."""
        key = self.key_of(scope="read")
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(load_json(INSTANCE_PATH)),
            headers=auth_header(key),
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_read_only", response.json["error_code"])
        self.assertIn("read-only", response.json["error"])
        response = self.client.put(
            f"{USER_URL}{self.planner.id}/",
            data=json.dumps({"email": "other@example.com"}),
            headers=auth_header(key),
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_forbidden", response.json["error_code"])
        response = self.client.delete(API_KEY_URL, headers=auth_header(key))
        self.assertEqual(403, response.status_code)
        self.assertEqual("api_key_forbidden", response.json["error_code"])

    def test_uat_8_9_cli_issues_read_only_key_without_totp(self):
        """8.9 cornflow users api_key -u <user> --read-only issues a read-only key."""
        self.enroll_if_relaxed("cfplanner")
        if is_strict():
            self.token_of("cfplanner")
        with capture_audit() as audit:
            result = self.run_cli("users", "api_key", "-u", "cfplanner", "--read-only")
        self.assertEqual(0, result.exit_code, result.output)
        key = result.output.strip().splitlines()[-1]
        self.assertTrue(self.user_row("cfplanner").mfa_enabled)
        self.assertEqual("read", self.user_row("cfplanner").api_key_scope)
        self.assertEqual(200, self.get_instances(key).status_code)
        issued = audit.by_event("apikey.issued")
        self.assertEqual(1, len(issued))
        self.assertEqual("read", issued[0]["scope"])
        self.assertEqual("cli", issued[0]["source"])

    def test_uat_8_10_previous_key_works_in_grace(self):
        """8.10 Generate a new key: the previous one works inside the grace window."""
        grace = int(SETTINGS["API_KEY_ROTATION_GRACE_MINUTES"])
        self.assertGreater(grace, 0)
        first = self.key_of()
        second = self.key_of()
        self.assertEqual(200, self.get_instances(second).status_code)
        self.assertEqual(200, self.get_instances(first).status_code)
        with freeze_time(datetime.now(timezone.utc) + timedelta(minutes=grace - 1)):
            self.assertEqual(200, self.get_instances(first).status_code)

    def test_uat_8_11_previous_key_dies_after_grace(self):
        """8.11 After API_KEY_ROTATION_GRACE_MINUTES the previous key is 401."""
        grace = int(SETTINGS["API_KEY_ROTATION_GRACE_MINUTES"])
        first = self.key_of()
        second = self.key_of()
        with freeze_time(datetime.now(timezone.utc) + timedelta(minutes=grace + 1)):
            response = self.get_instances(first)
            self.assertEqual(401, response.status_code)
            self.assertEqual(REVOKED_MESSAGE, response.json["error"])
            self.assertEqual(200, self.get_instances(second).status_code)

    def test_uat_8_12_grace_covers_only_the_previous_key(self):
        """8.12 Generate three keys and use the oldest: 401."""
        oldest = self.key_of()
        middle = self.key_of()
        newest = self.key_of()
        response = self.get_instances(oldest)
        self.assertEqual(401, response.status_code)
        self.assertEqual(REVOKED_MESSAGE, response.json["error"])
        self.assertEqual(200, self.get_instances(middle).status_code)
        self.assertEqual(200, self.get_instances(newest).status_code)

    def test_uat_8_13_explicit_revocation_has_no_grace(self):
        """8.13 DELETE /user/api-key/ and use the revoked key: 401 at once."""
        first = self.key_of()
        second = self.key_of()
        token = self.token_of("cfplanner")
        response = self.client.delete(API_KEY_URL, headers=auth_header(token))
        self.assertEqual(200, response.status_code)
        self.assertEqual("The API key has been revoked", response.json["message"])
        for key in (second, first):
            response = self.get_instances(key)
            self.assertEqual(401, response.status_code)
            self.assertEqual(REVOKED_MESSAGE, response.json["error"])

    def test_uat_8_14_locking_the_account_revokes_its_keys(self):
        """8.14 Lock the account and use its key: 401."""
        key = self.key_of()
        self.assertEqual(200, self.get_instances(key).status_code)
        for _ in range(int(SETTINGS["LOGIN_MAX_ATTEMPTS"])):
            self.login("cfplanner", password="Wrong-pass.1x")
        self.assertTrue(self.user_row("cfplanner").locked)
        response = self.get_instances(key)
        self.assertEqual(401, response.status_code)
        self.assertEqual(REVOKED_MESSAGE, response.json["error"])
        # unlocking does not bring the key back
        admin_token = self.token_of("cfplatform")
        response = self.client.put(
            f"{USER_URL}{self.planner.id}/unlock/", headers=auth_header(admin_token)
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(401, self.get_instances(key).status_code)

    def test_uat_8_15_password_change_keeps_the_key(self):
        """8.15 Change the password and use the key: it keeps working."""
        key = self.key_of()
        token = self.token_of("cfplanner")
        response = self.client.put(
            f"{USER_URL}{self.planner.id}/",
            data=json.dumps(
                {"password": NEW_PASSWORD, "current_password": self.password_of("cfplanner")}
            ),
            headers=auth_header(token),
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(200, self.get_instances(key).status_code)

    def test_uat_8_16_notify_expiry_with_fresh_key_sends_nothing(self):
        """8.16 notify-expiry with a newly created key: 0 API key(s)."""
        self.key_of()
        with self.fake_smtp() as _:
            from cornflow.tests.uat_hardening_support import FakeSMTP

            result = self.run_cli("tokens", "notify-expiry", "-v")
            self.assertEqual([], FakeSMTP.sent)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Sent expiry warnings for 0 API key(s)", result.output)

    def test_uat_8_17_notify_expiry_sends_email_with_real_days(self):
        """8.17 Backdate the key to 29 days left: owner and platform admins are mailed."""
        from cornflow.tests.uat_hardening_support import FakeSMTP

        self.key_of()
        self.age_key("cfplanner", 29)
        with capture_audit() as audit, self.fake_smtp():
            result = self.run_cli("tokens", "notify-expiry", "-v")
            sent = list(FakeSMTP.sent)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Sent expiry warnings for 1 API key(s)", result.output)
        receivers = sorted(receiver for mail in sent for receiver in mail["to"])
        self.assertEqual(["cfplanner@example.com", "cfplatform@example.com"], receivers)
        for mail in sent:
            self.assertIn("29 day(s)", str(mail["message"]))
        event = audit.by_event("apikey.expiry_notified")[0]
        self.assertEqual(29, event["days_left"])
        self.assertEqual(30, event["threshold"])
        self.assertTrue(event["email_sent"])

    def test_uat_8_18_notify_expiry_is_idempotent(self):
        """8.18 Run the command again the same day: nothing is sent."""
        from cornflow.tests.uat_hardening_support import FakeSMTP

        self.key_of()
        self.age_key("cfplanner", 29)
        with self.fake_smtp():
            self.run_cli("tokens", "notify-expiry")
            self.assertEqual(2, len(FakeSMTP.sent))
            for _ in range(2):
                result = self.run_cli("tokens", "notify-expiry")
                self.assertIn("for 0 API key(s)", result.output)
            self.assertEqual(2, len(FakeSMTP.sent))
        self.assertEqual(30, self.user_row("cfplanner").api_key_expiry_notified)

    def test_uat_8_19_notify_expiry_next_threshold(self):
        """8.19 Leave 2 days and run: the next warning is sent."""
        from cornflow.tests.uat_hardening_support import FakeSMTP

        self.key_of()
        self.age_key("cfplanner", 29)
        with self.fake_smtp():
            self.run_cli("tokens", "notify-expiry")
            FakeSMTP.sent.clear()
            self.age_key("cfplanner", 2)
            result = self.run_cli("tokens", "notify-expiry")
            sent = list(FakeSMTP.sent)
        self.assertIn("for 1 API key(s)", result.output)
        self.assertEqual(2, len(sent))
        for mail in sent:
            self.assertIn("2 day(s)", str(mail["message"]))
        self.assertEqual(2, self.user_row("cfplanner").api_key_expiry_notified)

    def test_uat_8_20_regenerating_restarts_the_warnings(self):
        """8.20 Regenerate the key and run: warnings restart for the new key."""
        from cornflow.tests.uat_hardening_support import FakeSMTP

        self.key_of()
        self.age_key("cfplanner", 2)
        with self.fake_smtp():
            self.run_cli("tokens", "notify-expiry")
            self.assertEqual(2, self.user_row("cfplanner").api_key_expiry_notified)
            self.key_of()
            self.assertIsNone(self.user_row("cfplanner").api_key_expiry_notified)
            FakeSMTP.sent.clear()
            result = self.run_cli("tokens", "notify-expiry")
            self.assertIn("for 0 API key(s)", result.output)
            self.assertEqual([], FakeSMTP.sent)
            # the cycle starts over: 29 days left warns again (threshold 30)
            self.age_key("cfplanner", 29)
            result = self.run_cli("tokens", "notify-expiry")
            self.assertIn("for 1 API key(s)", result.output)
        self.assertEqual(30, self.user_row("cfplanner").api_key_expiry_notified)

    def test_uat_8_21_notify_expiry_without_email_config(self):
        """8.21 Without SERVICE_EMAIL_* run the command: log warning and audit event."""
        for name in (
            "SERVICE_EMAIL_ADDRESS",
            "SERVICE_EMAIL_PASSWORD",
            "SERVICE_EMAIL_SERVER",
            "SERVICE_EMAIL_PORT",
        ):
            current_app.config[name] = None
        self.key_of()
        self.age_key("cfplanner", 28)
        with capture_audit() as audit, self.assertLogs(
            current_app.logger, level="WARNING"
        ) as logs:
            result = self.run_cli("tokens", "notify-expiry")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(
            any(
                "Email is not configured" in line and "28 day(s)" in line
                for line in logs.output
            ),
            logs.output,
        )
        event = audit.by_event("apikey.expiry_notified")[0]
        self.assertEqual(28, event["days_left"])
        self.assertEqual(30, event["threshold"])
        self.assertEqual(2, event["recipients"])
        self.assertFalse(event["email_sent"])

    def test_uat_8_22_service_account_key_serves_airflow(self):
        """8.22 Service account key (CORNFLOW_SERVICE_API_KEY): server side only."""
        # Airflow itself cannot run here: only the server side is checked, i.e.
        # that the service user's key reaches the endpoints airflow uses and
        # that using it does not involve any login.
        self.make_user("service_user", [SERVICE_ROLE])
        result = self.run_cli("users", "api_key", "-u", "service_user")
        self.assertEqual(0, result.exit_code, result.output)
        key = result.output.strip().splitlines()[-1]
        planner_token = self.token_of("cfplanner")
        instance = self.client.post(
            INSTANCE_URL,
            data=json.dumps(load_json(INSTANCE_PATH)),
            headers=auth_header(planner_token),
        ).json["id"]
        execution_payload = {**load_json(EXECUTION_PATH), "instance_id": instance}
        execution = self.client.post(
            EXECUTION_URL_NORUN,
            data=json.dumps(execution_payload),
            headers=auth_header(planner_token),
        ).json["id"]
        with capture_audit() as audit:
            deployed = self.client.get(DEPLOYED_DAG_URL, headers=auth_header(key))
            self.assertEqual(200, deployed.status_code, deployed.json)
            data = self.client.get(f"{DAG_URL}{execution}/", headers=auth_header(key))
            self.assertEqual(200, data.status_code, data.json)
            put = self.client.put(
                f"{DAG_URL}{execution}/",
                data=json.dumps({"state": 1}),
                headers=auth_header(key),
            )
            self.assertEqual(200, put.status_code, put.json)
        self.assertEqual([], audit.by_event("login.success"))


class TestUatApiKeysDisabled(CommonSetup):
    config_overrides = {"PERSONAL_TOKEN_ENABLED": 0}

    def test_uat_8_23_personal_token_disabled_is_501(self):
        """8.23 PERSONAL_TOKEN_ENABLED=0 and generate a key: 501 (section hiding is UI)."""
        token = self.token_of("cfplanner")
        response = self.client.post(
            API_KEY_URL, data=json.dumps({}), headers=auth_header(token)
        )
        self.assertEqual(501, response.status_code)
        self.assertIn("disabled", response.json["error"])
        # the server part of the case only: the settings page of cornflow-ui
        # hides the section depending on its own build parameter


# ---------------------------------------------------------------------------
# Block 10: audit
# ---------------------------------------------------------------------------


class TestUatAudit(CommonSetup):
    def test_uat_10_1_login_success(self):
        """10.1 Successful login: login.success with actor, ip, method."""
        self.full_login("cfplanner")  # enrols when MFA is required
        with capture_audit() as audit:
            self.full_login("cfplanner")
        events = audit.by_event("login.success")
        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual("cfplanner", event["actor"])
        self.assertEqual(self.planner.id, event["actor_id"])
        self.assertEqual("db", event["method"])
        self.assertTrue(event["ip"])

    def test_uat_10_2_wrong_password(self):
        """10.2 Wrong password: login.failure with reason bad_password."""
        with capture_audit() as audit:
            self.login("cfplanner", password="Wrong-pass.1x")
        event = audit.by_event("login.failure")[0]
        self.assertEqual("bad_password", event["reason"])
        self.assertEqual("cfplanner", event["actor"])
        self.assertTrue(event["ip"])

    def test_uat_10_3_unknown_user(self):
        """10.3 Unknown user: login.failure with reason unknown_user."""
        with capture_audit() as audit:
            self.login("nobody-here", password="Wrong-pass.1x")
        event = audit.by_event("login.failure")[0]
        self.assertEqual("unknown_user", event["reason"])

    def test_uat_10_4_lock_by_attempts(self):
        """10.4 Lock by attempts: account.locked with the number of attempts."""
        attempts = int(SETTINGS["LOGIN_MAX_ATTEMPTS"])
        with capture_audit() as audit:
            for _ in range(attempts):
                self.login("cfplanner", password="Wrong-pass.1x")
        event = audit.by_event("account.locked")[0]
        self.assertEqual("cfplanner", event["target"])
        self.assertEqual(attempts, event["attempts"])

    def test_uat_10_5_unlock(self):
        """10.5 Unlock: account.unlocked with actor and target."""
        for _ in range(int(SETTINGS["LOGIN_MAX_ATTEMPTS"])):
            self.login("cfplanner", password="Wrong-pass.1x")
        token = self.token_of("cfplatform")
        with capture_audit() as audit:
            response = self.client.put(
                f"{USER_URL}{self.planner.id}/unlock/", headers=auth_header(token)
            )
        self.assertEqual(200, response.status_code, response.json)
        event = audit.by_event("account.unlocked")[0]
        self.assertEqual("cfplatform", event["actor"])
        self.assertEqual("cfplanner", event["target"])
        self.assertEqual(self.planner.id, event["target_id"])

    def test_uat_10_6_password_changed(self):
        """10.6 Password change: password.changed."""
        token = self.token_of("cfplanner")
        with capture_audit() as audit:
            response = self.client.put(
                f"{USER_URL}{self.planner.id}/",
                data=json.dumps(
                    {
                        "password": NEW_PASSWORD,
                        "current_password": self.password_of("cfplanner"),
                    }
                ),
                headers=auth_header(token),
            )
        self.assertEqual(200, response.status_code, response.json)
        event = audit.by_event("password.changed")[0]
        self.assertEqual("cfplanner", event["actor"])
        self.assertEqual("cfplanner", event["target"])

    def test_uat_10_7_mfa_enrolled_and_reset(self):
        """10.7 MFA enrolment and reset: mfa.enrolled, mfa.reset."""
        with capture_audit() as audit:
            if is_strict():
                self.token_of("cfplanner")
            else:
                self.enroll_if_relaxed("cfplanner")
        event = audit.by_event("mfa.enrolled")[0]
        self.assertEqual("cfplanner", event["actor"])
        token = self.token_of("cfplatform")
        with capture_audit() as audit:
            response = self.client.delete(
                f"{USER_URL}{self.planner.id}/mfa/", headers=auth_header(token)
            )
        self.assertEqual(200, response.status_code, response.json)
        event = audit.by_event("mfa.reset")[0]
        self.assertEqual("cfplatform", event["actor"])
        self.assertEqual("cfplanner", event["target"])

    def test_uat_10_8_apikey_issued_and_revoked(self):
        """10.8 Key issue and revocation: apikey.issued (scope), apikey.revoked."""
        with capture_audit() as audit:
            self.mint("cfplanner", scope="read")
            token = self.token_of("cfplanner")
            response = self.client.delete(API_KEY_URL, headers=auth_header(token))
        self.assertEqual(200, response.status_code)
        issued = audit.by_event("apikey.issued")[0]
        self.assertEqual("read", issued["scope"])
        self.assertEqual("cfplanner", issued["actor"])
        self.assertIn("expires_at", issued)
        revoked = audit.by_event("apikey.revoked")[0]
        self.assertEqual("cfplanner", revoked["actor"])

    def test_uat_10_9_role_granted_and_revoked(self):
        """10.9 Role grant / revoke: role.granted, role.revoked."""
        admin = self.make_user("cfadmin", [ADMIN_ROLE])
        target = self.make_user("cfviewer", [VIEWER_ROLE])
        token = self.token_of("cfadmin")
        with capture_audit() as audit:
            response = self.client.post(
                USER_ROLE_URL,
                data=json.dumps({"user_id": target.id, "role_id": PLANNER_ROLE}),
                headers=auth_header(token),
            )
            self.assertEqual(201, response.status_code, response.json)
            response = self.client.delete(
                f"{USER_ROLE_URL}{target.id}/{PLANNER_ROLE}/",
                headers=auth_header(token),
            )
            self.assertEqual(200, response.status_code, response.json)
        granted = audit.by_event("role.granted")[0]
        self.assertEqual("cfadmin", granted["actor"])
        self.assertEqual(admin.id, granted["actor_id"])
        self.assertEqual(target.id, granted["target_id"])
        self.assertEqual(PLANNER_ROLE, granted["role_id"])
        revoked = audit.by_event("role.revoked")[0]
        self.assertEqual("cfadmin", revoked["actor"])
        self.assertEqual(target.id, revoked["target_id"])
        self.assertEqual(PLANNER_ROLE, revoked["role_id"])

    @pending_fix("4deffdf5")
    def test_uat_10_10_session_refreshed_and_logout_have_actor(self):
        """10.10 Refresh and logout: session.refreshed, session.logout (with actor)."""
        login = self.full_login("cfplanner")
        with capture_audit() as audit:
            refreshed = self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": login["refresh_token"]}),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(200, refreshed.status_code, refreshed.json)
            logout = self.client.post(
                LOGOUT_URL,
                data=json.dumps({"refresh_token": refreshed.json["refresh_token"]}),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(200, logout.status_code)
        self.assertEqual(
            "cfplanner", audit.by_event("session.refreshed")[0].get("actor")
        )
        self.assertEqual("cfplanner", audit.by_event("session.logout")[0].get("actor"))

    def test_uat_10_11_refresh_reuse_detected(self):
        """10.11 Reuse of a refresh token: session.reuse_detected, outcome revoked."""
        login = self.full_login("cfplanner")
        headers = {"Content-Type": "application/json"}
        rotated = self.client.post(
            REFRESH_URL,
            data=json.dumps({"refresh_token": login["refresh_token"]}),
            headers=headers,
        )
        self.assertEqual(200, rotated.status_code, rotated.json)
        with capture_audit() as audit:
            replay = self.client.post(
                REFRESH_URL,
                data=json.dumps({"refresh_token": login["refresh_token"]}),
                headers=headers,
            )
        self.assertEqual(401, replay.status_code)
        event = audit.by_event("session.reuse_detected")[0]
        self.assertEqual("revoked", event["outcome"])
        self.assertEqual("cfplanner", event["actor"])
        self.assertTrue(event["ip"])
        self.assertTrue(event["session_id"])

    def test_uat_10_12_expiry_notified(self):
        """10.12 Expiry warning: apikey.expiry_notified with days_left and threshold."""
        self.key_of()
        self.age_key("cfplanner", 29)
        with capture_audit() as audit, self.fake_smtp():
            self.run_cli("tokens", "notify-expiry")
        event = audit.by_event("apikey.expiry_notified")[0]
        self.assertEqual("cfplanner", event["target"])
        self.assertEqual(29, event["days_left"])
        self.assertEqual(30, event["threshold"])
        self.assertEqual(2, event["recipients"])
        self.assertTrue(event["email_sent"])

    def test_uat_10_13_audit_can_be_disabled(self):
        """10.13 AUDIT_LOG_ENABLED=0 and repeat a login: no audit event."""
        current_app.config["AUDIT_LOG_ENABLED"] = 0
        try:
            self.full_login("cfplanner")
            with capture_audit() as audit:
                self.full_login("cfplanner")
                self.login("cfplanner", password="Wrong-pass.1x")
                self.login("nobody-here", password="Wrong-pass.1x")
            self.assertEqual([], audit.records)
        finally:
            current_app.config["AUDIT_LOG_ENABLED"] = 1
        with capture_audit() as audit:
            self.full_login("cfplanner")
        self.assertEqual(1, len(audit.by_event("login.success")))


# ---------------------------------------------------------------------------
# Block 11: headers, CORS, docs
# ---------------------------------------------------------------------------


class TestUatHeaders(CommonSetup):
    def test_uat_11_1_security_headers(self):
        """11.1 GET /health/ carries the six security headers."""
        response = self.client.get(HEALTH_URL)
        headers = response.headers
        self.assertEqual("nosniff", headers["X-Content-Type-Options"])
        self.assertEqual("DENY", headers["X-Frame-Options"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual("no-referrer", headers["Referrer-Policy"])
        self.assertIn("camera=()", headers["Permissions-Policy"])
        self.assertEqual("no-store", headers["Cache-Control"])

    def test_uat_11_2_server_header_does_not_reveal_versions(self):
        """11.2 The Server header does not reveal Werkzeug/Flask; no X-Powered-By."""
        response = self.client.get(HEALTH_URL)
        server = response.headers.get("Server", "")
        for word in ("werkzeug", "flask", "python"):
            self.assertNotIn(word, server.lower())
        self.assertFalse(any(char.isdigit() for char in server), server)
        self.assertNotIn("X-Powered-By", response.headers)


class TestUatHsts(CommonSetup):
    config_overrides = {"RATELIMIT_TRUST_FORWARDED_FOR": 1, "HSTS_ENABLED": 1}

    def test_uat_11_3_hsts_behind_tls(self):
        """11.3 With TLS in front and HSTS_ENABLED=1: Strict-Transport-Security."""
        response = self.client.get(
            HEALTH_URL, headers={"X-Forwarded-Proto": "https"}
        )
        hsts = response.headers["Strict-Transport-Security"]
        self.assertIn("max-age=", hsts)
        self.assertIn("includeSubDomains", hsts)


class TestUatCorsClosed(CommonSetup):
    config_overrides = {"CORS_ORIGINS": ""}

    def test_uat_11_4_no_cors_by_default(self):
        """11.4 Without CORS_ORIGINS an foreign Origin gets no Allow-Origin."""
        response = self.client.get(HEALTH_URL, headers={"Origin": "https://foreign.example"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        preflight = self.client.options(
            LOGIN_URL,
            headers={
                "Origin": "https://foreign.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotIn("Access-Control-Allow-Origin", preflight.headers)


class TestUatCorsOpen(CommonSetup):
    config_overrides = {"CORS_ORIGINS": "https://mi-ui"}

    def test_uat_11_5_cors_allows_listed_origin(self):
        """11.5 With CORS_ORIGINS=https://mi-ui a request with that Origin is allowed."""
        response = self.client.get(HEALTH_URL, headers={"Origin": "https://mi-ui"})
        self.assertEqual("https://mi-ui", response.headers["Access-Control-Allow-Origin"])
        foreign = self.client.get(HEALTH_URL, headers={"Origin": "https://foreign.example"})
        self.assertNotIn("Access-Control-Allow-Origin", foreign.headers)


class TestUatDocsOff(CommonSetup):
    config_overrides = {"DOCS_ENABLED": 0}

    def test_uat_11_6_docs_disabled_in_production(self):
        """11.6 GET /swagger-ui/ and /swagger/ in production: 404."""
        self.assertEqual(404, self.client.get("/swagger-ui/").status_code)
        self.assertEqual(404, self.client.get("/swagger/").status_code)


class TestUatDocsOn(CommonSetup):
    config_overrides = {"DOCS_ENABLED": 1}

    def test_uat_11_7_docs_enabled(self):
        """11.7 With CORNFLOW_DOCS_ENABLED=1 the documentation answers again."""
        self.assertEqual(200, self.client.get("/swagger-ui/").status_code)
        self.assertEqual(200, self.client.get("/swagger/").status_code)


class TestUatUi(CommonSetup):
    @ui_only("browser console (CSP errors) with the complete interface")
    def test_uat_11_8_ui_runs_with_headers(self):
        """11.8 Full interface against the production server: no CSP errors."""


# ---------------------------------------------------------------------------
# Block 12: functional regression
# ---------------------------------------------------------------------------


class TestUatRegression(CommonSetup):
    def create_instance_and_execution(self, token, run=True):
        instance = self.client.post(
            INSTANCE_URL,
            data=json.dumps(load_json(INSTANCE_PATH)),
            headers=auth_header(token),
        )
        self.assertEqual(201, instance.status_code, instance.json)
        instance_id = instance.json["id"]
        payload = {**load_json(EXECUTION_PATH), "instance_id": instance_id}
        url = EXECUTION_URL if run else EXECUTION_URL_NORUN
        patcher = airflow_mock() if run else None
        try:
            execution = self.client.post(
                url, data=json.dumps(payload), headers=auth_header(token)
            )
        finally:
            if patcher:
                patcher.stop()
        self.assertEqual(201, execution.status_code, execution.json)
        return instance_id, execution.json["id"]

    def solve_as_service(self, service_token, execution_id, expected_get=200):
        """What airflow does: read the data, write the solution back."""
        data = self.client.get(
            f"{DAG_URL}{execution_id}/", headers=auth_header(service_token)
        )
        self.assertEqual(expected_get, data.status_code, data.json)
        if expected_get != 200:
            return
        self.assertIn("data", data.json)
        # the solution schema of this DAG is the same as its instance schema
        solution = {"state": 1, "data": load_json(INSTANCE_PATH)["data"]}
        response = self.client.put(
            f"{DAG_URL}{execution_id}/",
            data=json.dumps(solution),
            headers=auth_header(service_token),
        )
        self.assertEqual(200, response.status_code, response.json)

    @pending_fix("42b50338")
    def test_uat_12_1_instance_execution_solution_flow(self):
        """12.1 Create an instance, launch an execution and fetch the solution."""
        self.make_user("service_user", [SERVICE_ROLE])
        service_token = self.token_of("service_user")
        # regular (client side) planner
        token = self.token_of("cfplanner")
        instance_id, execution_id = self.create_instance_and_execution(token)
        queued = self.client.get(
            f"{EXECUTION_URL}{execution_id}/", headers=auth_header(token)
        )
        self.assertEqual(200, queued.status_code, queued.json)
        self.assertEqual(-7, queued.json["state"])  # queued in the (mocked) Airflow
        self.solve_as_service(service_token, execution_id)
        results = self.client.get(
            f"{EXECUTION_URL}{execution_id}/", headers=auth_header(token)
        )
        self.assertEqual(1, results.json["state"])
        solution = self.client.get(
            f"{EXECUTION_URL}{execution_id}/data/", headers=auth_header(token)
        )
        self.assertEqual(200, solution.status_code, solution.json)
        self.assertEqual(load_json(INSTANCE_PATH)["data"], solution.json["data"])
        # platform user: the service account must still read their data
        self.make_user("cfplatformplanner", [PLATFORM_PLANNER_ROLE])
        platform_token = self.token_of("cfplatformplanner")
        _, platform_execution = self.create_instance_and_execution(platform_token)
        self.solve_as_service(service_token, platform_execution)

    def test_uat_12_2_case_from_instance_and_execution_and_compare(self):
        """12.2 Create a case from an instance / execution and compare them."""
        token = self.token_of("cfplanner")
        instance_id, execution_id = self.create_instance_and_execution(token, run=False)
        base = {"name": "case from instance", "schema": "solve_model_dag"}
        from_instance = self.client.post(
            CASE_INSTANCE_URL,
            data=json.dumps({**base, "instance_id": instance_id}),
            headers=auth_header(token),
        )
        self.assertEqual(201, from_instance.status_code, from_instance.json)
        from_execution = self.client.post(
            CASE_INSTANCE_URL,
            data=json.dumps(
                {**base, "name": "case from execution", "execution_id": execution_id}
            ),
            headers=auth_header(token),
        )
        self.assertEqual(201, from_execution.status_code, from_execution.json)
        compare = self.client.get(
            f"{CASE_URL}{from_instance.json['id']}/{from_execution.json['id']}/",
            headers=auth_header(token),
        )
        self.assertEqual(200, compare.status_code, compare.json)
        self.assertIn("data_patch", compare.json)
        self.assertIn("solution_patch", compare.json)
        # same instance data in both cases: no difference in the data
        self.assertEqual([], compare.json["data_patch"])

    def test_uat_12_3_schemas_and_deployed_dags(self):
        """12.3 Query the schemas and the deployed DAGs."""
        # users created through /signup/ get the DAG permissions of an open
        # deployment; users created straight in the database need them added
        PermissionsDAG.add_all_permissions_to_user(self.planner.id)
        token = self.token_of("cfplanner")
        schemas = self.client.get(SCHEMA_URL, headers=auth_header(token))
        self.assertEqual(200, schemas.status_code, schemas.json)
        names = {item["name"] for item in schemas.json}
        self.assertIn("solve_model_dag", names)
        detail = self.client.get(
            f"{SCHEMA_URL}solve_model_dag/", headers=auth_header(token)
        )
        self.assertEqual(200, detail.status_code, detail.json)
        self.make_user("service_user", [SERVICE_ROLE])
        service_token = self.token_of("service_user")
        deployed = self.client.get(DEPLOYED_DAG_URL, headers=auth_header(service_token))
        self.assertEqual(200, deployed.status_code, deployed.json)
        self.assertEqual(names, {item["id"] for item in deployed.json})

    def make_client(self):
        """cornflow-client talking to the Flask test client."""
        from cornflow_client import CornFlow

        patcher = patch(
            "cornflow_client.raw_cornflow_client.requests",
            FlaskRequests(self.client),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return CornFlow(url="http://localhost" + PREFIX + "/")

    def test_uat_12_4_cornflow_client_flow(self):
        """12.4 cornflow-client: login, create instance, run, read results."""
        self.token_of("cfplanner")  # enrols MFA when the profile requires it
        client = self.make_client()
        totp = self.totp_now("cfplanner") if "cfplanner" in self.mfa_secrets else None
        body = client.login("cfplanner", self.password_of("cfplanner"), totp_code=totp)
        self.assertIn("token", body)
        self.assertTrue(client.token)
        data = load_json(INSTANCE_PATH)
        instance = client.create_instance(data["data"], name="client instance")
        self.assertTrue(instance["id"])
        patcher = airflow_mock()
        try:
            execution = client.create_execution(
                instance["id"],
                load_json(EXECUTION_PATH)["config"],
                name="client execution",
            )
        finally:
            patcher.stop()
        execution_id = execution["id"]
        # the service account (airflow) writes the solution back
        self.make_user("service_user", [SERVICE_ROLE])
        service_token = self.token_of("service_user")
        self.solve_as_service(service_token, execution_id)
        results = client.get_results(execution_id)
        self.assertEqual(1, results["state"])
        self.assertEqual("client execution", results["name"])
        solution = client.get_solution(execution_id)
        self.assertEqual(load_json(INSTANCE_PATH)["data"], solution["data"])

    @pending_fix("4deffdf5")
    def test_uat_12_5_client_renews_expired_access_token(self):
        """12.5 cornflow-client working longer than the access token duration."""
        self.token_of("cfplanner")
        client = self.make_client()
        totp = self.totp_now("cfplanner") if "cfplanner" in self.mfa_secrets else None
        client.login("cfplanner", self.password_of("cfplanner"), totp_code=totp)
        self.assertIsInstance(client.get_all_instances(), list)
        minutes = int(SETTINGS["ACCESS_TOKEN_DURATION_MINUTES"]) + 1
        with freeze_time(datetime.now(timezone.utc) + timedelta(minutes=minutes)):
            # server contract: an expired access token is a 401
            expired = self.client.get(
                INSTANCE_URL, headers=auth_header(client.token)
            )
            self.assertEqual(401, expired.status_code, expired.json)
            # and the client renews and retries transparently
            self.assertIsInstance(client.get_all_instances(), list)

    def test_uat_12_6_client_with_api_key_needs_no_login(self):
        """12.6 cornflow-client with set_api_key() works without login."""
        key = self.key_of()
        client = self.make_client()
        client.set_api_key(key)
        self.assertIsNone(client.refresh_token)
        self.assertIsInstance(client.get_all_instances(), list)

    @ui_only("instances, executions, cases and dashboard screens of cornflow-ui")
    def test_uat_12_7_ui_screens(self):
        """12.7 Interface: instances, executions, cases and dashboard."""

    def test_uat_12_8_bi_token_cli_and_deprecation_note(self):
        """12.8 cornflow users bi_token issues a token; deprecated in the docs."""
        with capture_audit() as audit:
            result = self.run_cli("users", "bi_token", "-u", "cfplanner")
        self.assertEqual(0, result.exit_code, result.output)
        token = result.output.strip().splitlines()[-1]
        self.assertTrue(token)
        self.assertEqual(1, len(audit.by_event("bitoken.issued")))
        with open(ACCESS_RST, encoding="utf-8") as handler:
            text = handler.read()
        self.assertIn("BI tokens (deprecated)", text)
        self.assertIn("BI tokens are **deprecated**", text)
