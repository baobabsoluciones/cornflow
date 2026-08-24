"""
Unit tests for the refresh-token session flow (ENS op.acc — session
management): the sliding inactivity window (Model B), the absolute session
cap, stateful session storage, rotation, reuse detection, logout and the
refusal to use a refresh token on a normal endpoint.
"""

import json
import logging
import unittest
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_testing import TestCase

from cornflow.app import _check_session_windows, create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.models import SessionModel, UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import SERVICE_ROLE
from cornflow.tests.const import LOGIN_URL, SIGNUP_URL, USER_URL, PREFIX

REFRESH_URL = PREFIX + "/token/refresh/"
LOGOUT_URL = PREFIX + "/logout/"

STRONG_PASSWORD = "Kx9#tR2m!Qw7Zp"
OTHER_STRONG_PASSWORD = "Nw5@rT8y!Kd3Zx"
JSON_HEADER = {"Content-Type": "application/json"}


def auth_header(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


class TestRefreshTokenFlow(TestCase):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(False)
        register_deployed_dags_command_test(verbose=False)
        self.data = {
            "username": "refreshuser",
            "email": "refresh@test.com",
            "password": STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(self.data), headers=JSON_HEADER
        )
        self.user_id = response.json["id"]
        register_dag_permissions_command(
            open_deployment=int(current_app.config["OPEN_DEPLOYMENT"]), verbose=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self):
        return self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": self.data["username"], "password": self.data["password"]}
            ),
            headers=JSON_HEADER,
        )

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

    def _session(self):
        # setUp signs the user up (which opens a session too), so target the
        # most recent session — the one created by the login under test. The
        # expire_all forces a fresh read of state changed in another request.
        db.session.expire_all()
        return (
            SessionModel.query.filter_by(user_id=self.user_id)
            .order_by(SessionModel.id.desc())
            .first()
        )

    # -- issuance ----------------------------------------------------------

    def test_login_returns_access_and_refresh(self):
        response = self.login()
        self.assertEqual(200, response.status_code)
        self.assertIn("token", response.json)
        self.assertIn("refresh_token", response.json)
        # a stateful session was created
        session = self._session()
        self.assertIsNotNone(session)
        self.assertFalse(session.revoked)

    def test_access_token_works_on_normal_endpoint(self):
        token = self.login().json["token"]
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(token)
        )
        self.assertEqual(200, response.status_code)

    def test_refresh_token_rejected_on_normal_endpoint(self):
        refresh_token = self.login().json["refresh_token"]
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(refresh_token)
        )
        self.assertEqual(401, response.status_code)

    # -- rotation ----------------------------------------------------------

    def test_refresh_returns_new_pair(self):
        login = self.login().json
        response = self.refresh(login["refresh_token"])
        self.assertEqual(200, response.status_code)
        self.assertIn("token", response.json)
        self.assertIn("refresh_token", response.json)
        # the refresh token was rotated
        self.assertNotEqual(login["refresh_token"], response.json["refresh_token"])
        # the new access token works
        check = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(response.json["token"])
        )
        self.assertEqual(200, check.status_code)

    def test_reuse_of_old_refresh_token_revokes_session(self):
        login = self.login().json
        # first rotation: the original refresh token is now superseded
        rotated = self.refresh(login["refresh_token"]).json["refresh_token"]
        # replaying the original (superseded) token is detected as reuse
        replay = self.refresh(login["refresh_token"])
        self.assertEqual(401, replay.status_code)
        # and the whole session is revoked: even the valid rotated token fails
        after = self.refresh(rotated)
        self.assertEqual(401, after.status_code)

    # -- inactivity / absolute cap ----------------------------------------

    def test_inactivity_window_closes_session(self):
        refresh_token = self.login().json["refresh_token"]
        window = int(current_app.config["REFRESH_TOKEN_INACTIVITY_MINUTES"])
        session = self._session()
        session.last_activity_at = datetime.now(timezone.utc) - timedelta(
            minutes=window + 5
        )
        db.session.add(session)
        db.session.commit()
        response = self.refresh(refresh_token)
        self.assertEqual(401, response.status_code)

    def test_absolute_cap_closes_session(self):
        refresh_token = self.login().json["refresh_token"]
        session = self._session()
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.add(session)
        db.session.commit()
        response = self.refresh(refresh_token)
        self.assertEqual(401, response.status_code)

    def test_activity_slides_the_window(self):
        # a refresh well within the window keeps the session alive; a second
        # refresh with the rotated token still succeeds
        refresh_token = self.login().json["refresh_token"]
        new_refresh = self.refresh(refresh_token).json["refresh_token"]
        self.assertEqual(200, self.refresh(new_refresh).status_code)

    # -- the access token dies with its session ----------------------------

    def test_reuse_detection_kills_the_access_token_in_circulation(self):
        # UAT 6.5: revoking the session on reuse detection must also stop the
        # access tokens already issued, not only the renewal
        login = self.login().json
        rotated = self.refresh(login["refresh_token"]).json
        # replaying the superseded refresh token revokes the session
        self.assertEqual(401, self.refresh(login["refresh_token"]).status_code)
        # neither the access token minted by the refresh...
        self.assertEqual(
            401,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(rotated["token"])
            ).status_code,
        )
        # ...nor the one issued at login keep working
        self.assertEqual(
            401,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(login["token"])
            ).status_code,
        )

    def test_logout_kills_the_access_token_in_circulation(self):
        # same hole on the logout path: clicking "log out" must end access now
        login = self.login().json
        self.assertEqual(200, self.logout(login["refresh_token"]).status_code)
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(login["token"])
        )
        self.assertEqual(401, response.status_code)

    def test_absolute_cap_kills_the_access_token(self):
        login = self.login().json
        session = self._session()
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.add(session)
        db.session.commit()
        self.assertEqual(
            401,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(login["token"])
            ).status_code,
        )

    def test_revoking_one_session_leaves_the_others_alive(self):
        # each login is an independent session: closing one must not close the
        # rest (only a global event such as a password change does that)
        first = self.login().json
        second = self.login().json
        self.logout(first["refresh_token"])
        self.assertEqual(
            401,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(first["token"])
            ).status_code,
        )
        self.assertEqual(
            200,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(second["token"])
            ).status_code,
        )

    def test_inactivity_does_not_break_an_active_access_token(self):
        # the session-state check must NOT enforce the inactivity window, or a
        # user making requests without refreshing would be logged out
        login = self.login().json
        session = self._session()
        window = int(current_app.config["REFRESH_TOKEN_INACTIVITY_MINUTES"])
        session.last_activity_at = datetime.now(timezone.utc) - timedelta(
            minutes=window + 5
        )
        db.session.add(session)
        db.session.commit()
        # the access token still works (it is the refresh that would fail)
        self.assertEqual(
            200,
            self.client.get(
                f"{USER_URL}{self.user_id}/", headers=auth_header(login["token"])
            ).status_code,
        )
        self.assertEqual(401, self.refresh(login["refresh_token"]).status_code)

    def test_legacy_token_without_session_still_works(self):
        # tokens issued before sessions were bound carry no "sid": they must
        # keep working so upgrading a deployment does not log everybody out
        from cornflow.shared.authentication import Auth

        legacy = Auth.generate_token(self.user_id)
        response = self.client.get(
            f"{USER_URL}{self.user_id}/", headers=auth_header(legacy)
        )
        self.assertEqual(200, response.status_code)

    # -- revocation --------------------------------------------------------

    def test_logout_revokes_session(self):
        refresh_token = self.login().json["refresh_token"]
        self.assertEqual(200, self.logout(refresh_token).status_code)
        self.assertEqual(401, self.refresh(refresh_token).status_code)
        self.assertTrue(self._session().revoked)

    def test_logout_is_idempotent(self):
        refresh_token = self.login().json["refresh_token"]
        self.logout(refresh_token)
        # logging out again (invalid/revoked token) still succeeds
        self.assertEqual(200, self.logout(refresh_token).status_code)

    def test_password_change_revokes_refresh(self):
        login = self.login().json
        token, refresh_token = login["token"], login["refresh_token"]
        change = self.client.put(
            f"{USER_URL}{self.user_id}/",
            data=json.dumps(
                {
                    "password": OTHER_STRONG_PASSWORD,
                    "current_password": STRONG_PASSWORD,
                }
            ),
            headers=auth_header(token),
        )
        self.assertEqual(200, change.status_code)
        # the token version was bumped, so the refresh token is rejected
        self.assertEqual(401, self.refresh(refresh_token).status_code)

    def test_missing_refresh_token_is_rejected(self):
        response = self.client.post(
            REFRESH_URL, data=json.dumps({}), headers=JSON_HEADER
        )
        self.assertEqual(400, response.status_code)

    # -- service users / feature toggle -----------------------------------

    def test_service_user_gets_no_refresh_token(self):
        data = {
            "username": "svcuser",
            "email": "svc@test.com",
            "password": OTHER_STRONG_PASSWORD,
        }
        response = self.client.post(
            SIGNUP_URL, data=json.dumps(data), headers=JSON_HEADER
        )
        UserRoleModel({"user_id": response.json["id"], "role_id": SERVICE_ROLE}).save()
        login = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": data["username"], "password": data["password"]}
            ),
            headers=JSON_HEADER,
        )
        self.assertEqual(200, login.status_code)
        self.assertIn("token", login.json)
        self.assertNotIn("refresh_token", login.json)

    def test_feature_disabled_returns_single_token(self):
        current_app.config["REFRESH_TOKEN_ENABLED"] = 0
        try:
            login = self.login()
            self.assertEqual(200, login.status_code)
            self.assertIn("token", login.json)
            self.assertNotIn("refresh_token", login.json)
        finally:
            current_app.config["REFRESH_TOKEN_ENABLED"] = 1

    # -- housekeeping / audit ----------------------------------------------

    def test_login_purges_stale_sessions(self):
        # revoke everything open so far (the signup in setUp also opened a
        # session): those rows are now stale
        SessionModel.revoke_all_for_user(self.user_id)
        db.session.commit()

        # this login purges the revoked rows and opens a fresh session
        self.login()
        db.session.expire_all()
        rows = SessionModel.query.filter_by(user_id=self.user_id).all()
        self.assertEqual(1, len(rows))
        self.assertFalse(rows[0].revoked)

        # make it expired: the next login purges it too
        rows[0].expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.add(rows[0])
        db.session.commit()
        self.login()
        db.session.expire_all()
        remaining = SessionModel.query.filter_by(user_id=self.user_id).all()
        self.assertEqual(1, len(remaining))
        self.assertFalse(remaining[0].revoked)

    def test_purge_stale_leaves_active_sessions(self):
        self.login()
        before = SessionModel.query.filter_by(user_id=self.user_id).count()
        deleted = SessionModel.purge_stale()
        db.session.commit()
        self.assertEqual(0, deleted)
        self.assertEqual(
            before, SessionModel.query.filter_by(user_id=self.user_id).count()
        )

    def test_reuse_detection_emits_audit_event(self):
        import logging

        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        capture = _Capture()
        audit_logger = logging.getLogger("cornflow.audit")
        audit_logger.addHandler(capture)
        try:
            login = self.login().json
            self.refresh(login["refresh_token"])
            # replaying the superseded token trips the reuse detection
            self.refresh(login["refresh_token"])
        finally:
            audit_logger.removeHandler(capture)
        events = [json.loads(r) for r in records if "reuse_detected" in r]
        self.assertEqual(1, len(events))
        self.assertEqual("session.reuse_detected", events[0]["event"])
        self.assertEqual(self.user_id, events[0]["actor_id"])
        self.assertEqual("revoked", events[0]["outcome"])


class TestSessionWindowSanityCheck(unittest.TestCase):
    """
    The inactivity window must be longer than the access-token lifetime: a
    client only refreshes once its access token has expired, so a shorter
    window would log out users who are actively working. The application
    reports the misconfiguration at startup (it is stricter, not laxer, so it
    is not clamped).
    """

    def _warnings(self, **config):
        app = create_app("testing")
        app.config.update(config)
        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        handler = _Capture()
        app.logger.addHandler(handler)
        try:
            _check_session_windows(app)
        finally:
            app.logger.removeHandler(handler)
        return records

    def test_no_warning_with_the_defaults(self):
        self.assertEqual(
            [],
            self._warnings(
                ACCESS_TOKEN_DURATION_MINUTES=15,
                REFRESH_TOKEN_INACTIVITY_MINUTES=30,
                REFRESH_TOKEN_ABSOLUTE_HOURS=12,
            ),
        )

    def test_warns_when_the_window_is_not_longer_than_the_access_token(self):
        warnings = self._warnings(
            ACCESS_TOKEN_DURATION_MINUTES=15,
            REFRESH_TOKEN_INACTIVITY_MINUTES=10,
            REFRESH_TOKEN_ABSOLUTE_HOURS=12,
        )
        self.assertTrue(
            any("REFRESH_TOKEN_INACTIVITY_MINUTES" in w for w in warnings),
            msg=f"expected a warning, got {warnings}",
        )

    def test_warns_when_the_window_equals_the_access_token(self):
        warnings = self._warnings(
            ACCESS_TOKEN_DURATION_MINUTES=15,
            REFRESH_TOKEN_INACTIVITY_MINUTES=15,
            REFRESH_TOKEN_ABSOLUTE_HOURS=12,
        )
        self.assertTrue(any("actively working" in w for w in warnings))

    def test_warns_when_the_absolute_cap_swallows_the_window(self):
        warnings = self._warnings(
            ACCESS_TOKEN_DURATION_MINUTES=15,
            REFRESH_TOKEN_INACTIVITY_MINUTES=120,
            REFRESH_TOKEN_ABSOLUTE_HOURS=1,
        )
        self.assertTrue(
            any("REFRESH_TOKEN_ABSOLUTE_HOURS" in w for w in warnings),
            msg=f"expected a warning, got {warnings}",
        )

    def test_silent_when_refresh_sessions_are_disabled(self):
        self.assertEqual(
            [],
            self._warnings(
                REFRESH_TOKEN_ENABLED=0,
                ACCESS_TOKEN_DURATION_MINUTES=15,
                REFRESH_TOKEN_INACTIVITY_MINUTES=1,
                REFRESH_TOKEN_ABSOLUTE_HOURS=12,
            ),
        )
