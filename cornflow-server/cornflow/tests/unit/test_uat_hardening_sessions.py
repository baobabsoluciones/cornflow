"""
UAT battery of the security hardening, group B: password recovery (block 5),
sessions, renewal and inactivity timeout (block 6), platform roles and data
isolation (block 7) and attribution of the changes made by the service
account (block 9).

Each test is named after the id of its case in the UAT sheet. Run it in both
profiles with ``CORNFLOW_UAT_PROFILE=strict|relaxed`` (see
``cornflow/tests/uat_hardening_support.py``).
"""

import email as email_lib
import json
import re
from datetime import datetime, timedelta, timezone

import jwt
from click.testing import CliRunner
from flask import current_app, g
from freezegun import freeze_time

from cornflow.cli import cli
from cornflow.models import ExecutionModel, InstanceModel, SessionModel, UserModel
from cornflow.shared import db
from cornflow.shared.const import (
    ADMIN_ROLE,
    PLANNER_ROLE,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_PLANNER_ROLE,
    PLATFORM_ROLES,
    PLATFORM_VIEWER_ROLE,
    SERVICE_ROLE,
)
from cornflow.tests.const import (
    CASE_PATH,
    EXECUTION_PATH,
    EXECUTION_URL,
    EXECUTION_URL_NORUN,
    DAG_URL,
    INSTANCE_PATH,
    INSTANCE_URL,
    PREFIX,
    ROLES_URL,
    USER_URL,
)
from cornflow.tests.uat_hardening_support import (
    SETTINGS,
    FakeSMTP,
    UatTestCase,
    auth_header,
    is_relaxed,
    JSON_HEADER,
    pending_fix,
    ui_only,
)

RECOVER_URL = PREFIX + "/user/recover-password/"
RESET_URL = PREFIX + "/user/reset-password/"
REFRESH_URL = PREFIX + "/token/refresh/"
LOGOUT_URL = PREFIX + "/logout/"
USER_ROLE_URL = PREFIX + "/user/role/"

UI_URL = "https://cornflow-ui.example.com"
NEW_PASSWORD = "Jp7-nDv.Bf8Tk2"
THIRD_PASSWORD = "Hq3-sLw.Yc6Mz4"

ACCESS_MINUTES = int(SETTINGS["ACCESS_TOKEN_DURATION_MINUTES"])
INACTIVITY_MINUTES = int(SETTINGS["REFRESH_TOKEN_INACTIVITY_MINUTES"])


def load_file(path):
    with open(path) as handler:
        return json.load(handler)


def clock():
    """Frozen clock starting now (naive UTC, as freezegun expects)."""
    return freeze_time(datetime.now(timezone.utc).replace(tzinfo=None))


class SessionsTestCase(UatTestCase):
    """Helpers shared by the cases of this group."""

    def get(self, url, token):
        return self.client.get(url, headers=auth_header(token))

    def refresh(self, refresh_token):
        return self.client.post(
            REFRESH_URL,
            data=json.dumps({"refresh_token": refresh_token}),
            headers=JSON_HEADER,
        )

    def logout(self, refresh_token):
        return self.client.post(
            LOGOUT_URL,
            data=json.dumps({"refresh_token": refresh_token}),
            headers=JSON_HEADER,
        )

    def audit_events(self, logs):
        events = []
        for line in logs.output:
            payload = line.split(":", 2)[-1]
            try:
                events.append(json.loads(payload))
            except ValueError:
                continue
        return events

    def last_session(self, user_id):
        db.session.expire_all()
        return (
            SessionModel.query.filter_by(user_id=user_id)
            .order_by(SessionModel.id.desc())
            .first()
        )

    def create_instance(self, token, expected=201):
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(load_file(INSTANCE_PATH)),
            headers=auth_header(token),
        )
        self.assertEqual(expected, response.status_code, response.json)
        return response.json.get("id")

    def create_execution(self, token, instance_id):
        payload = {**load_file(EXECUTION_PATH), "instance_id": instance_id}
        response = self.client.post(
            EXECUTION_URL_NORUN, data=json.dumps(payload), headers=auth_header(token)
        )
        self.assertEqual(201, response.status_code, response.json)
        return response.json["id"]

    def ids(self, url, token):
        response = self.get(url, token)
        self.assertEqual(200, response.status_code, response.json)
        return [item["id"] for item in response.json]

    def grant(self, token, user_id, role_id):
        return self.client.post(
            USER_ROLE_URL,
            data=json.dumps({"user_id": user_id, "role_id": role_id}),
            headers=auth_header(token),
        )

    def revoke(self, token, user_id, role_id):
        return self.client.delete(
            f"{USER_ROLE_URL}{user_id}/{role_id}/", headers=auth_header(token)
        )


class TestUatPasswordRecovery(SessionsTestCase):
    """Block 5: password recovery."""

    def setUp(self):
        super().setUp()
        current_app.config["CORNFLOW_UI_URL"] = UI_URL
        self.user = self.make_user("recoveruser", [PLANNER_ROLE])

    def request_recovery(self, address):
        with self.fake_smtp():
            response = self.client.put(
                RECOVER_URL,
                data=json.dumps({"email": address}),
                headers=JSON_HEADER,
            )
            sent = list(FakeSMTP.sent)
        return response, sent

    def token_from(self, sent):
        self.assertEqual(1, len(sent))
        message = email_lib.message_from_string(sent[0]["message"])
        body = ""
        for part in message.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode("utf-8")
        match = re.search(rf"{re.escape(UI_URL)}/reset-password\?token=([\w\.\-]+)", body)
        self.assertIsNotNone(match, body)
        return match.group(1)

    def reset(self, token, password=NEW_PASSWORD):
        return self.client.put(
            RESET_URL,
            data=json.dumps({"password": password}),
            headers=auth_header(token),
        )

    def test_uat_5_1_recovery_existing_email_sends_link(self):
        """5.1 Request a recovery with an existing e-mail: neutral 200 and a
        mail with a link to CORNFLOW_UI_URL/reset-password?token=..."""
        response, sent = self.request_recovery(self.user.email)
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("message", response.json)
        self.assertEqual([self.user.email], sent[0]["to"])
        self.assertTrue(self.token_from(sent))

    def test_uat_5_2_recovery_unknown_email_same_response(self):
        """5.2 Request a recovery with a non-existent e-mail: same response
        and message (accounts cannot be enumerated)."""
        known, _ = self.request_recovery(self.user.email)
        unknown, sent = self.request_recovery("nobody@example.com")
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json, unknown.json)
        self.assertEqual([], sent)

    def test_uat_5_3_reset_link_sets_valid_password(self):
        """5.3 Open the link and set a valid password: 200 and the new
        password can be used to log in."""
        _, sent = self.request_recovery(self.user.email)
        token = self.token_from(sent)
        response = self.reset(token)
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(200, self.login("recoveruser", NEW_PASSWORD).status_code)
        self.assertNotEqual(200, self.login("recoveruser").status_code)

    def test_uat_5_4_reset_link_is_single_use(self):
        """5.4 Reuse the same link: clear error (single use)."""
        _, sent = self.request_recovery(self.user.email)
        token = self.token_from(sent)
        self.assertEqual(200, self.reset(token).status_code)
        response = self.reset(token, THIRD_PASSWORD)
        self.assertEqual(401, response.status_code, response.json)
        self.assertIn("error", response.json)

    def test_uat_5_5_reset_token_is_purpose_restricted(self):
        """5.5 Use the link token against another endpoint (e.g. GET
        /instance/): 403, the token only serves its purpose."""
        _, sent = self.request_recovery(self.user.email)
        token = self.token_from(sent)
        for url in (INSTANCE_URL, USER_URL, EXECUTION_URL):
            response = self.get(url, token)
            self.assertEqual(403, response.status_code, url)
            self.assertEqual("purpose_token", response.json.get("error_code"), url)
        # against its own endpoint the same token is valid
        self.assertEqual(200, self.reset(token).status_code)

    @pending_fix("4deffdf5")
    def test_uat_5_6_reset_link_expires(self):
        """5.6 Wait more than PWD_RESET_TOKEN_DURATION_MINUTES and open the
        link: expired-link error."""
        minutes = int(current_app.config["PWD_RESET_TOKEN_DURATION_MINUTES"])
        with clock() as frozen:
            _, sent = self.request_recovery(self.user.email)
            token = self.token_from(sent)
            frozen.tick(timedelta(minutes=minutes + 1))
            response = self.reset(token)
        self.assertEqual(401, response.status_code, response.json)
        self.assertIn("expired", response.json["error"].lower())
        # the old password was not replaced
        self.assertEqual(200, self.login("recoveruser").status_code)


class TestUatSessions(SessionsTestCase):
    """Block 6: sessions, renewal and inactivity timeout."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("sessionuser", [PLANNER_ROLE])

    def open_session(self, username="sessionuser"):
        return self.full_login(username)

    def test_uat_6_1_login_returns_tokens_and_stores_session(self):
        """6.1 Log in (interactive user): token and refresh_token are returned
        and a row exists in session_tokens."""
        # the first login enrolls the user when the profile requires MFA
        self.open_session()
        with self.assertLogs("cornflow.audit", level="INFO") as logs:
            body = self.open_session()
        self.assertIn("token", body)
        self.assertIn("refresh_token", body)
        session = self.last_session(self.user.id)
        self.assertIsNotNone(session)
        self.assertFalse(session.revoked)
        events = [e["event"] for e in self.audit_events(logs)]
        self.assertIn("login.success", events)

    def test_uat_6_2_access_token_works(self):
        """6.2 Use the token in GET /instance/: 200."""
        token = self.open_session()["token"]
        self.assertEqual(200, self.get(INSTANCE_URL, token).status_code)

    def test_uat_6_3_refresh_token_rejected_on_normal_endpoint(self):
        """6.3 Use the refresh_token in GET /instance/: 401, a refresh token
        is not valid on normal endpoints."""
        refresh_token = self.open_session()["refresh_token"]
        self.assertEqual(401, self.get(INSTANCE_URL, refresh_token).status_code)

    def test_uat_6_4_refresh_rotates_tokens(self):
        """6.4 POST /token/refresh/ with the refresh_token: 200 with a new
        token and a new refresh_token (rotation)."""
        body = self.open_session()
        with clock() as frozen:
            frozen.tick(timedelta(seconds=5))
            response = self.refresh(body["refresh_token"])
        self.assertEqual(200, response.status_code, response.json)
        self.assertNotEqual(body["token"], response.json["token"])
        self.assertNotEqual(body["refresh_token"], response.json["refresh_token"])

    @pending_fix("2f64a0df")
    def test_uat_6_5_refresh_reuse_revokes_session(self):
        """6.5 Repeat POST /token/refresh/ with the old refresh_token: 401 and
        the session is revoked; the new token is no longer valid either."""
        body = self.open_session()
        rotated = self.refresh(body["refresh_token"])
        self.assertEqual(200, rotated.status_code)
        replay = self.refresh(body["refresh_token"])
        self.assertEqual(401, replay.status_code)
        self.assertEqual(401, self.refresh(rotated.json["refresh_token"]).status_code)
        self.assertTrue(self.last_session(self.user.id).revoked)
        # the access tokens already issued die with the session
        self.assertEqual(401, self.get(INSTANCE_URL, rotated.json["token"]).status_code)
        self.assertEqual(401, self.get(INSTANCE_URL, body["token"]).status_code)

    @pending_fix("4deffdf5")
    def test_uat_6_6_expired_access_token_gives_401(self):
        """6.6 Wait longer than the access token duration and use the access
        token: 401 (expired)."""
        with clock() as frozen:
            token = self.open_session()["token"]
            frozen.tick(timedelta(minutes=ACCESS_MINUTES - 1))
            self.assertEqual(200, self.get(INSTANCE_URL, token).status_code)
            frozen.tick(timedelta(minutes=2))
            response = self.get(INSTANCE_URL, token)
        self.assertEqual(401, response.status_code, response.json)

    def test_uat_6_7_refresh_inside_inactivity_window_slides_it(self):
        """6.7 After 6.6, refresh inside the inactivity window: 200, the
        session stays alive and the window slides."""
        with clock() as frozen:
            body = self.open_session()
            frozen.tick(timedelta(minutes=ACCESS_MINUTES + 1))
            first = self.refresh(body["refresh_token"])
            self.assertEqual(200, first.status_code, first.json)
            self.assertEqual(200, self.get(INSTANCE_URL, first.json["token"]).status_code)
            # the total time since login exceeds the window but not the time
            # since the last refresh: the window has slid
            frozen.tick(timedelta(minutes=INACTIVITY_MINUTES - 1))
            second = self.refresh(first.json["refresh_token"])
            self.assertEqual(200, second.status_code, second.json)

    def test_uat_6_8_inactivity_window_closes_session(self):
        """6.8 Wait longer than the inactivity window without refreshing and
        then refresh: 401, session closed for inactivity."""
        with clock() as frozen:
            body = self.open_session()
            frozen.tick(timedelta(minutes=INACTIVITY_MINUTES + 1))
            response = self.refresh(body["refresh_token"])
        self.assertEqual(401, response.status_code, response.json)

    def test_uat_6_9_logout_revokes_session(self):
        """6.9 POST /logout/ with the refresh_token: 200, a later refresh
        gives 401 and the row is revoked."""
        body = self.open_session()
        response = self.logout(body["refresh_token"])
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(401, self.refresh(body["refresh_token"]).status_code)
        self.assertTrue(self.last_session(self.user.id).revoked)

    def test_uat_6_10_logout_is_idempotent(self):
        """6.10 POST /logout/ again with the same token: 200 (idempotent)."""
        body = self.open_session()
        self.assertEqual(200, self.logout(body["refresh_token"]).status_code)
        self.assertEqual(200, self.logout(body["refresh_token"]).status_code)

    def test_uat_6_11_password_change_revokes_sessions(self):
        """6.11 Change the password and refresh with a previous token: 401,
        the change revokes every session."""
        body = self.open_session()
        change = self.client.put(
            f"{USER_URL}{self.user.id}/",
            data=json.dumps(
                {
                    "password": NEW_PASSWORD,
                    "current_password": self.password_of("sessionuser"),
                }
            ),
            headers=auth_header(body["token"]),
        )
        self.assertEqual(200, change.status_code, change.json)
        self.assertEqual(401, self.refresh(body["refresh_token"]).status_code)
        self.assertEqual(401, self.get(INSTANCE_URL, body["token"]).status_code)

    def test_uat_6_12_service_user_gets_long_lived_token_only(self):
        """6.12 Service user login: only a token (no refresh_token), long
        lived."""
        self.make_user("svcuser", [SERVICE_ROLE])
        response = self.login("svcuser")
        self.assertEqual(200, response.status_code, response.json)
        self.assertIn("token", response.json)
        self.assertNotIn("refresh_token", response.json)
        claims = jwt.decode(
            response.json["token"],
            current_app.config["SECRET_TOKEN_KEY"],
            algorithms=["HS256"],
        )
        lifetime = claims["exp"] - claims["iat"]
        self.assertGreater(lifetime, ACCESS_MINUTES * 60)
        self.assertEqual(
            int(float(current_app.config["TOKEN_DURATION"]) * 3600), lifetime
        )

    @ui_only("inactivity redirect to the login screen with an expired-session notice")
    def test_uat_6_13_ui_inactivity_redirects_to_login(self):
        """6.13 In the UI, leave the tab idle longer than the window and
        click any action: redirect to login with an expired-session notice."""

    @pending_fix("4deffdf5")
    def test_uat_6_14_continuous_work_renews_transparently(self):
        """6.14 Work continuously longer than the access token duration:
        nothing is noticed, the token is renewed transparently (server part:
        refreshing keeps the session alive; an unrenewed token answers 401)."""
        with clock() as frozen:
            body = self.open_session()
            for _ in range(3):
                frozen.tick(timedelta(minutes=ACCESS_MINUTES - 1))
                self.assertEqual(200, self.get(INSTANCE_URL, body["token"]).status_code)
                renewed = self.refresh(body["refresh_token"])
                self.assertEqual(200, renewed.status_code, renewed.json)
                body = renewed.json
            # without renewing, the token expires and the client is told so
            # with the status code that triggers the renewal
            frozen.tick(timedelta(minutes=ACCESS_MINUTES + 1))
            self.assertEqual(401, self.get(INSTANCE_URL, body["token"]).status_code)

    @ui_only("file download after the access token expires (renew and retry)")
    def test_uat_6_15_ui_download_after_token_expiry(self):
        """6.15 In the UI, download a file (Excel) after the access token
        expires: the download works (renews and retries)."""

    @pending_fix("4deffdf5")
    def test_uat_6_16_logout_revokes_and_audits_actor(self):
        """6.16 Log out: the session is revoked on the server and the
        session.logout event is audited with who closed it."""
        body = self.open_session()
        # the logout carries no credential: forget the user of the previous
        # request kept by the test context so the actor must come from the
        # closed session
        g.pop("user", None)
        with self.assertLogs("cornflow.audit", level="INFO") as logs:
            self.assertEqual(200, self.logout(body["refresh_token"]).status_code)
        self.assertTrue(self.last_session(self.user.id).revoked)
        events = [e for e in self.audit_events(logs) if e["event"] == "session.logout"]
        self.assertEqual(1, len(events))
        self.assertIn("ts", events[0])
        self.assertIn("ip", events[0])
        self.assertEqual(self.user.id, events[0].get("actor_id"))

    def test_uat_6_17_sessions_purge_cli(self):
        """6.17 cornflow sessions purge: deletes the expired/revoked rows and
        reports the number."""
        body = self.open_session()
        self.logout(body["refresh_token"])
        db.session.commit()
        stale = SessionModel.query.filter_by(revoked=True).count()
        self.assertGreaterEqual(stale, 1)
        result = CliRunner().invoke(cli, ["sessions", "purge"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(f"Deleted {stale} stale sessions", result.output)
        db.session.expire_all()
        self.assertEqual(0, SessionModel.query.filter_by(revoked=True).count())


class TestUatPlatformRoles(SessionsTestCase):
    """Block 7: platform roles and data isolation."""

    def setUp(self):
        super().setUp()
        self.viewer = self.make_user("pviewer", [PLATFORM_VIEWER_ROLE])
        self.planner = self.make_user("pplanner", [PLATFORM_PLANNER_ROLE])
        self.padmin = self.make_user("padmin", [PLATFORM_ADMIN_ROLE])
        self.cadmin = self.make_user("cadmin", [ADMIN_ROLE])
        self.cplanner = self.make_user("cplanner", [PLANNER_ROLE])
        self.target = self.make_user("target", [PLANNER_ROLE])

    def isolated_resources(self):
        """A platform instance + execution next to a client one."""
        pinstance = self.create_instance(self.token_of("pplanner"))
        pexecution = self.create_execution(self.token_of("pplanner"), pinstance)
        cinstance = self.create_instance(self.token_of("cplanner"))
        cexecution = self.create_execution(self.token_of("cplanner"), cinstance)
        return pinstance, pexecution, cinstance, cexecution

    def test_uat_7_1_platform_viewer_reads_instances(self):
        """7.1 platform_viewer does GET /instance/: 200 (read, like a
        viewer)."""
        response = self.get(INSTANCE_URL, self.token_of("pviewer"))
        self.assertEqual(200, response.status_code)

    def test_uat_7_2_platform_viewer_cannot_create_instance(self):
        """7.2 platform_viewer does POST /instance/: 403 (no write
        permission)."""
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(load_file(INSTANCE_PATH)),
            headers=auth_header(self.token_of("pviewer")),
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(0, InstanceModel.query.count())

    def test_uat_7_3_platform_planner_creates_instance(self):
        """7.3 platform_planner creates an instance: 201 (like a planner)."""
        instance_id = self.create_instance(self.token_of("pplanner"))
        stored = InstanceModel.get_one_object(idx=instance_id)
        self.assertEqual(self.planner.id, stored.user_id)

    def test_uat_7_4_platform_non_admins_cannot_manage_users_or_roles(self):
        """7.4 platform_viewer / platform_planner access GET /user/ or
        /roles/: 403, they are not administrators."""
        for username in ("pviewer", "pplanner"):
            token = self.token_of(username)
            for url in (USER_URL, ROLES_URL):
                self.assertEqual(403, self.get(url, token).status_code, (username, url))

    def test_uat_7_5_client_admin_cannot_grant_platform_admin(self):
        """7.5 Client admin tries to grant platform_admin (POST /user/role/
        with role_id=903): 403, only a platform admin grants platform roles."""
        response = self.grant(self.token_of("cadmin"), self.target.id, PLATFORM_ADMIN_ROLE)
        self.assertEqual(403, response.status_code)
        self.assertIn("Only a platform administrator", response.json["error"])
        # the same call by a platform admin works
        response = self.grant(self.token_of("padmin"), self.target.id, PLATFORM_ADMIN_ROLE)
        self.assertIn(response.status_code, (200, 201), response.json)

    def test_uat_7_6_client_admin_cannot_revoke_platform_viewer(self):
        """7.6 Client admin tries to revoke platform_viewer from a user: 403."""
        self.assertIn(
            self.grant(self.token_of("padmin"), self.target.id, PLATFORM_VIEWER_ROLE).status_code,
            (200, 201),
        )
        response = self.revoke(self.token_of("cadmin"), self.target.id, PLATFORM_VIEWER_ROLE)
        self.assertEqual(403, response.status_code)
        self.assertIn("Only a platform administrator", response.json["error"])

    def test_uat_7_7_platform_admin_grants_and_revokes_platform_planner(self):
        """7.7 Platform admin grants and revokes platform_planner: 200/201 in
        both cases, audited."""
        token = self.token_of("padmin")
        with self.assertLogs("cornflow.audit", level="INFO") as logs:
            granted = self.grant(token, self.target.id, PLATFORM_PLANNER_ROLE)
            revoked = self.revoke(token, self.target.id, PLATFORM_PLANNER_ROLE)
        self.assertIn(granted.status_code, (200, 201), granted.json)
        self.assertEqual(200, revoked.status_code, revoked.json)
        events = {e["event"]: e for e in self.audit_events(logs)}
        for name in ("role.granted", "role.revoked"):
            self.assertEqual(self.padmin.id, events[name]["actor_id"])
            self.assertEqual(self.target.id, events[name]["target_id"])
            self.assertEqual(PLATFORM_PLANNER_ROLE, events[name]["role_id"])
        roles = self.get(USER_ROLE_URL, token)
        self.assertEqual(200, roles.status_code)

    def test_uat_7_8_client_admin_cannot_revoke_admin_role(self):
        """7.8 Client admin tries to remove the admin role from another admin:
        403 (only the platform can)."""
        other = self.make_user("otheradmin", [ADMIN_ROLE])
        response = self.revoke(self.token_of("cadmin"), other.id, ADMIN_ROLE)
        self.assertEqual(403, response.status_code)
        self.assertIn("Only a platform administrator", response.json["error"])
        response = self.revoke(self.token_of("padmin"), other.id, ADMIN_ROLE)
        self.assertEqual(200, response.status_code, response.json)

    def test_uat_7_9_client_admin_is_not_offered_platform_roles(self):
        """7.9 Editing a user as client admin: the platform_* roles are not
        offered (server part: GET /roles/, the source of the dropdown, is
        closed to client admins)."""
        response = self.get(ROLES_URL, self.token_of("cadmin"))
        self.assertEqual(403, response.status_code)

    def test_uat_7_10_platform_admin_is_offered_platform_roles(self):
        """7.10 Editing a user as platform admin: the platform_* roles do
        appear (server part: GET /roles/ lists them)."""
        response = self.get(ROLES_URL, self.token_of("padmin"))
        self.assertEqual(200, response.status_code)
        offered = {role["id"] for role in response.json}
        self.assertTrue(set(PLATFORM_ROLES) <= offered, offered)

    @pending_fix("e86f9a3f")
    def test_uat_7_11_client_planner_does_not_see_platform_data(self):
        """7.11 platform_planner creates an instance; list it as client
        planner: it does not appear."""
        pinstance, pexecution, cinstance, cexecution = self.isolated_resources()
        token = self.token_of("cplanner")
        self.assertNotIn(pinstance, self.ids(INSTANCE_URL, token))
        self.assertIn(cinstance, self.ids(INSTANCE_URL, token))
        self.assertNotIn(pexecution, self.ids(EXECUTION_URL, token))
        self.assertIn(cexecution, self.ids(EXECUTION_URL, token))

    @pending_fix("e86f9a3f")
    def test_uat_7_12_client_admin_does_not_see_platform_data(self):
        """7.12 The same instance, listed by a client admin: it does not
        appear (although the admin sees everything else of the client)."""
        pinstance, pexecution, cinstance, cexecution = self.isolated_resources()
        token = self.token_of("cadmin")
        instances = self.ids(INSTANCE_URL, token)
        self.assertNotIn(pinstance, instances)
        self.assertIn(cinstance, instances)
        executions = self.ids(EXECUTION_URL, token)
        self.assertNotIn(pexecution, executions)
        self.assertIn(cexecution, executions)

    def test_uat_7_13_platform_instance_by_id_is_404_for_client_admin(self):
        """7.13 Access that instance by id as client admin: 404 (existence is
        not confirmed)."""
        pinstance, pexecution, _, _ = self.isolated_resources()
        token = self.token_of("cadmin")
        self.assertEqual(404, self.get(f"{INSTANCE_URL}{pinstance}/", token).status_code)
        self.assertEqual(404, self.get(f"{EXECUTION_URL}{pexecution}/", token).status_code)

    def test_uat_7_14_platform_admin_sees_both_sides(self):
        """7.14 List as platform admin: sees the platform and the client
        instances."""
        pinstance, pexecution, cinstance, cexecution = self.isolated_resources()
        token = self.token_of("padmin")
        instances = self.ids(INSTANCE_URL, token)
        self.assertIn(pinstance, instances)
        self.assertIn(cinstance, instances)
        executions = self.ids(EXECUTION_URL, token)
        self.assertIn(pexecution, executions)
        self.assertIn(cexecution, executions)

    def test_uat_7_15_isolation_switch_off_shows_platform_data(self):
        """7.15 With PLATFORM_DATA_ISOLATION=0, repeat 7.12: the instance does
        appear (the off switch)."""
        pinstance, pexecution, cinstance, _ = self.isolated_resources()
        token = self.token_of("cadmin")
        current_app.config["PLATFORM_DATA_ISOLATION"] = 0
        try:
            self.assertIn(pinstance, self.ids(INSTANCE_URL, token))
            self.assertIn(pexecution, self.ids(EXECUTION_URL, token))
            self.assertEqual(200, self.get(f"{INSTANCE_URL}{pinstance}/", token).status_code)
            self.assertEqual(200, self.get(f"{EXECUTION_URL}{pexecution}/", token).status_code)
        finally:
            current_app.config["PLATFORM_DATA_ISOLATION"] = 1
        self.assertNotIn(pinstance, self.ids(INSTANCE_URL, token))
        self.assertEqual(404, self.get(f"{INSTANCE_URL}{pinstance}/", token).status_code)


class TestUatServiceAttribution(SessionsTestCase):
    """Block 9: attribution of the changes made by the service account."""

    def setUp(self):
        super().setUp()
        self.planner = self.make_user("owner", [PLANNER_ROLE])
        self.service = self.make_user("airflowuser", [SERVICE_ROLE])
        self.planner_token = self.token_of("owner")
        self.service_token = self.token_of("airflowuser")
        self.instance_id = self.create_instance(self.planner_token)
        self.execution_id = self.create_execution(self.planner_token, self.instance_id)

    def owner_of_execution(self):
        db.session.expire_all()
        return ExecutionModel.get_one_object(idx=self.execution_id).user_id

    def owner_of_instance(self):
        db.session.expire_all()
        return InstanceModel.get_one_object(idx=self.instance_id).user_id

    def solve(self):
        case = load_file(CASE_PATH)
        return self.client.put(
            f"{DAG_URL}{self.execution_id}/",
            data=json.dumps(
                {
                    "data": case["data"],
                    "state": 1,
                    "log_json": {"time": 1.5, "solver": "dummy", "status": "optimal"},
                }
            ),
            headers=auth_header(self.service_token),
        )

    def test_uat_9_1_execution_belongs_to_the_planner(self):
        """9.1 A planner creates an instance and launches an execution: the
        execution belongs to the planner."""
        self.assertEqual(self.planner.id, self.owner_of_instance())
        self.assertEqual(self.planner.id, self.owner_of_execution())

    def test_uat_9_2_solution_written_by_service_keeps_owner(self):
        """9.2 After the execution is resolved (airflow writes the solution),
        its user_id is still the planner's, not the service user's."""
        response = self.solve()
        self.assertEqual(200, response.status_code, response.json)
        db.session.expire_all()
        execution = ExecutionModel.get_one_object(idx=self.execution_id)
        self.assertEqual(1, execution.state)
        self.assertEqual(self.planner.id, execution.user_id)
        self.assertNotEqual(self.service.id, execution.user_id)
        self.assertEqual(self.planner.id, self.owner_of_instance())

    def test_uat_9_3_planner_still_sees_the_execution(self):
        """9.3 The planner lists their executions after the resolution: the
        execution is still visible."""
        self.assertEqual(200, self.solve().status_code)
        self.assertIn(self.execution_id, self.ids(EXECUTION_URL, self.planner_token))
        response = self.get(f"{EXECUTION_URL}{self.execution_id}/", self.planner_token)
        self.assertEqual(200, response.status_code)

    def test_uat_9_4_checks_written_by_service_keep_instance_owner(self):
        """9.4 Checks/KPIs written by airflow on an instance: the instance
        keeps its original owner."""
        response = self.client.put(
            f"{DAG_URL}instance/{self.instance_id}/",
            data=json.dumps({"checks": {}}),
            headers=auth_header(self.service_token),
        )
        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(self.planner.id, self.owner_of_instance())
        self.assertEqual(
            200,
            self.get(f"{INSTANCE_URL}{self.instance_id}/", self.planner_token).status_code,
        )
