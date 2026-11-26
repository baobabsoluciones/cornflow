"""
Tests of the per-IP rate limit that only counts failures (task011):

- login (database, LDAP and OpenID), token refresh and logout consume
  RATELIMIT_LOGIN only with responses of status 400 or above;
- the intermediate step of the MFA login (200 with mfa_required or
  mfa_setup_required) and the successful logins and refreshes do not consume;
- once the failures use up the limit the IP gets a 429, even with valid
  credentials, until the window passes; other IPs are not affected;
- password recovery and reset keep counting every request;
- RATELIMIT_ENABLED and RATELIMIT_TRUST_FORWARDED_FOR keep working as before;
- the per-IP limit is not the per-account lockout.

The behaviour is the same at the three security levels.

The expected values come from the specification and are written in this file
on purpose, not read from the code under test.
"""

import json
import time
import unittest
from unittest import mock

import pyotp
from flask import Response
from flask_testing import TestCase

from cornflow.commands.access import access_init_command
from cornflow.endpoints.login import LoginEndpoint, LoginOpenAuthEndpoint
from cornflow.endpoints.refresh import LogoutEndpoint, RefreshTokenEndpoint
from cornflow.endpoints.user import RecoverPassword, ResetPassword
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import (
    AUTH_LDAP,
    AUTH_OID,
    SERVICE_ROLE,
    TOKEN_PURPOSE_PWD_RESET,
    VIEWER_ROLE,
)
from cornflow.shared.exceptions import InvalidCredentials
from cornflow.shared import rate_limit
from cornflow.shared.rate_limit import limiter, login_rate_limit, recover_rate_limit
from cornflow.tests.const import LOGIN_URL, PREFIX, RECOVER_PASSWORD_URL
from cornflow.tests.security_levels_support import SecurityLevelTestMixin

RATE_LIMIT_MESSAGE_TEXT = "Too many requests. Please slow down and try again later."
BAD_TOTP_ERROR = "Invalid two-factor authentication code"

LEGACY_LOGIN_URL = "/login/"
REFRESH_URL = PREFIX + "/token/refresh/"
LEGACY_REFRESH_URL = "/token/refresh/"
LOGOUT_URL = PREFIX + "/logout/"
LEGACY_LOGOUT_URL = "/logout/"
RESET_PASSWORD_URL = PREFIX + "/user/reset-password/"

IP1 = "203.0.113.1"
IP2 = "203.0.113.2"

USER_PASSWORD = "Kx9#tR2m!Qw7Zp"
SERVICE_PASSWORD = "Sv7&kM2x!Bd5Ln"
WRONG_PASSWORD = "Wrong#Password9!x"
JSON_HEADER = {"Content-Type": "application/json"}

COMMON_OVERRIDES = {
    "RATELIMIT_ENABLED": 1,
    "RATELIMIT_LOGIN": "3 per minute",
    "RATELIMIT_RECOVER": "2 per hour",
}


def overrides(**extra):
    return {**COMMON_OVERRIDES, **extra}


def is_failed_response(response):
    # Looked up on call so that the rest of the module can run (and fail on
    # its own) while the function does not exist yet
    return rate_limit.is_failed_response(response)


class TestIsFailedResponse(unittest.TestCase):
    def test_success_codes_do_not_count(self):
        for status in (200, 201, 204, 302, 399):
            with self.subTest(status=status):
                self.assertFalse(is_failed_response(Response(status=status)))

    def test_error_codes_count(self):
        for status in (400, 401, 403, 404, 422, 429, 500, 503):
            with self.subTest(status=status):
                self.assertTrue(is_failed_response(Response(status=status)))


class TestLimitWiring(unittest.TestCase):
    def test_login_refresh_logout_count_only_failures(self):
        expected = [
            (LoginEndpoint, "login"),
            (LoginOpenAuthEndpoint, "login"),
            (RefreshTokenEndpoint, "token-refresh"),
            (LogoutEndpoint, "logout"),
        ]
        for endpoint, scope in expected:
            with self.subTest(endpoint=endpoint.__name__):
                self.assertEqual(1, len(endpoint.decorators))
                decorator = endpoint.decorators[0]
                self.assertIs(rate_limit.is_failed_response, decorator.deduct_when)
                self.assertIs(login_rate_limit, decorator.limit_value)
                self.assertTrue(decorator.shared)
                self.assertEqual(scope, decorator.scope)

    def test_recover_and_reset_count_every_request(self):
        expected = [
            (ResetPassword, "reset-password"),
            (RecoverPassword, "recover-password"),
        ]
        for endpoint, scope in expected:
            with self.subTest(endpoint=endpoint.__name__):
                self.assertEqual(1, len(endpoint.decorators))
                decorator = endpoint.decorators[0]
                self.assertIsNone(decorator.deduct_when)
                self.assertIs(recover_rate_limit, decorator.limit_value)
                self.assertTrue(decorator.shared)
                self.assertEqual(scope, decorator.scope)


class _RateLimitBase:
    """Common setup and helpers for the cases that need the application."""

    def setUp(self):
        self.reset_limiter()
        db.create_all()
        access_init_command(verbose=False)
        self.ana = self.make_user("ana", "ana@test.org", USER_PASSWORD, VIEWER_ROLE)
        self.service = self.make_user(
            "service_user", "service@test.org", SERVICE_PASSWORD, SERVICE_ROLE
        )

    def tearDown(self):
        self.reset_limiter()
        db.session.remove()
        db.drop_all()

    # helpers
    @staticmethod
    def reset_limiter():
        # The limiter has no storage while it is disabled
        if limiter.enabled:
            limiter.reset()

    @staticmethod
    def make_user(username, email, password, role):
        user = UserModel({"username": username, "email": email, "password": password})
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role}).save()
        return user

    def post(self, url, body, ip=IP1, headers=None):
        all_headers = dict(JSON_HEADER)
        all_headers.update(headers or {})
        return self.client.post(
            url,
            data=json.dumps(body),
            headers=all_headers,
            environ_base={"REMOTE_ADDR": ip},
        )

    def put(self, url, body, ip=IP1, headers=None):
        all_headers = dict(JSON_HEADER)
        all_headers.update(headers or {})
        return self.client.put(
            url,
            data=json.dumps(body),
            headers=all_headers,
            environ_base={"REMOTE_ADDR": ip},
        )

    def login(
        self, username, password, totp_code=None, ip=IP1, url=LOGIN_URL, headers=None
    ):
        body = {"username": username, "password": password}
        if totp_code is not None:
            body["totp_code"] = totp_code
        return self.post(url, body, ip=ip, headers=headers)

    def bad_login(self, ip=IP1, username="ana", url=LOGIN_URL, headers=None):
        return self.login(username, WRONG_PASSWORD, ip=ip, url=url, headers=headers)

    def good_login(self, ip=IP1, url=LOGIN_URL, headers=None):
        return self.login(
            "service_user", SERVICE_PASSWORD, ip=ip, url=url, headers=headers
        )

    def refresh(self, refresh_token, ip=IP1, url=REFRESH_URL):
        return self.post(url, {"refresh_token": refresh_token}, ip=ip)

    def logout(self, refresh_token, ip=IP1, url=LOGOUT_URL):
        return self.post(url, {"refresh_token": refresh_token}, ip=ip)

    def new_refresh_token(self):
        return Auth.issue_session_tokens(self.ana)["refresh_token"]

    def assert_rate_limited(self, response):
        self.assertEqual(429, response.status_code)
        self.assertEqual(RATE_LIMIT_MESSAGE_TEXT, response.json["message"])

    def assert_statuses(self, expected, responses):
        self.assertEqual(expected, [r.status_code for r in responses])


class _FailuresOnlyLoginCases(_RateLimitBase):
    """Cases of the database login, shared by the three levels."""

    # What the login of "ana" (viewer, not exempt from MFA) answers
    ana_login_has_token = True

    def test_successful_logins_do_not_consume(self):
        responses = [self.good_login() for _ in range(20)]
        self.assert_statuses([200] * 20, responses)
        for response in responses:
            self.assertIn("token", response.json)

    def test_internal_user_logins_do_not_consume(self):
        responses = [self.login("ana", USER_PASSWORD) for _ in range(20)]
        self.assert_statuses([200] * 20, responses)
        for response in responses:
            if self.ana_login_has_token:
                self.assertIn("token", response.json)
            else:
                self.assertTrue(response.json["mfa_setup_required"])
                self.assertIn("temp_token", response.json)

    def test_mixed_sequence(self):
        responses = [
            self.bad_login(),
            self.bad_login(),
            self.good_login(),
            self.bad_login(),
            self.good_login(),
        ]
        self.assert_statuses([400, 400, 200, 400, 429], responses)

    def test_failures_exhaust_the_limit_even_for_good_credentials(self):
        self.assert_statuses([400] * 3, [self.bad_login() for _ in range(3)])

        blocked = self.good_login()
        self.assert_rate_limited(blocked)
        self.assertEqual("3", blocked.headers.get("X-RateLimit-Limit"))
        self.assertIsNotNone(blocked.headers.get("Retry-After"))

        self.assertEqual(429, self.login("ana", USER_PASSWORD).status_code)

    def test_other_ip_still_logs_in(self):
        self.assert_statuses([400] * 3, [self.bad_login(ip=IP1) for _ in range(3)])
        self.assertEqual(200, self.good_login(ip=IP2).status_code)
        self.assertEqual(429, self.good_login(ip=IP1).status_code)

    def test_limit_resets_after_the_window(self):
        self.assert_statuses([400] * 3, [self.bad_login() for _ in range(3)])
        self.assertEqual(429, self.good_login().status_code)

        # Move the clock of the in-memory storage past the one minute window
        fake = mock.MagicMock()
        fake.time.return_value = time.time() + 61
        with mock.patch("limits.storage.memory.time", fake):
            self.assertEqual(200, self.good_login().status_code)

    def test_failures_from_different_usernames_share_the_ip_counter(self):
        responses = [self.bad_login(username=f"u{i}") for i in range(3)]
        self.assert_statuses([400] * 3, responses)
        self.assertEqual(429, self.good_login().status_code)

    def test_canonical_and_legacy_routes_share_the_counter(self):
        responses = [
            self.bad_login(url=LOGIN_URL),
            self.bad_login(url=LEGACY_LOGIN_URL),
            self.bad_login(url=LOGIN_URL),
        ]
        self.assert_statuses([400] * 3, responses)
        self.assertEqual(429, self.good_login(url=LEGACY_LOGIN_URL).status_code)

    def test_successes_on_legacy_route_do_not_consume(self):
        responses = [self.good_login(url=LEGACY_LOGIN_URL) for _ in range(10)]
        responses += [self.good_login(url=LOGIN_URL) for _ in range(10)]
        self.assert_statuses([200] * 20, responses)

    def test_remaining_header_only_drops_on_failures(self):
        remaining = []
        for step in (self.good_login, self.bad_login, self.good_login):
            response = step()
            remaining.append(response.headers.get("X-RateLimit-Remaining"))
        self.assertEqual(["3", "2", "2"], remaining)

    def test_ip_limit_is_not_the_account_lockout(self):
        self.assert_statuses([400] * 3, [self.bad_login(ip=IP1) for _ in range(3)])
        response = self.login("ana", USER_PASSWORD, ip=IP2)
        self.assertEqual(200, response.status_code)
        db.session.expire_all()
        self.assertFalse(UserModel.get_one_user_by_username("ana").locked)

    def test_forwarded_header_ignored_when_not_trusted(self):
        for _ in range(3):
            self.bad_login(headers={"X-Forwarded-For": "10.0.0.1"})
        response = self.good_login(headers={"X-Forwarded-For": "10.0.0.2"})
        self.assertEqual(429, response.status_code)


class TestFailuresOnlyLevel1(_FailuresOnlyLoginCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides()


class TestFailuresOnlyLevel2(_FailuresOnlyLoginCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = overrides()


class TestFailuresOnlyLevel3(_FailuresOnlyLoginCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = overrides()
    ana_login_has_token = False


class _FailuresOnlyMfaCases(_RateLimitBase):
    def setUp(self):
        super().setUp()
        self.secret = pyotp.random_base32()
        user = UserModel.get_one_user_by_username("ana")
        user.set_totp_secret(self.secret)
        user.mfa_enabled = True
        user.save()

    def test_mfa_required_step_does_not_consume(self):
        responses = [self.login("ana", USER_PASSWORD) for _ in range(5)]
        self.assert_statuses([200] * 5, responses)
        for response in responses:
            self.assertTrue(response.json["mfa_required"])

        complete = self.login("ana", USER_PASSWORD, totp_code=pyotp.TOTP(self.secret).now())
        self.assertEqual(200, complete.status_code)
        self.assertIn("token", complete.json)

    def test_wrong_totp_consumes(self):
        responses = [
            self.login("ana", USER_PASSWORD, totp_code="000000") for _ in range(3)
        ]
        self.assert_statuses([400] * 3, responses)
        for response in responses:
            self.assertEqual(BAD_TOTP_ERROR, response.json["error"])
        self.assertEqual(429, self.good_login().status_code)


class TestFailuresOnlyMfaLevel3(_FailuresOnlyMfaCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = overrides()


class TestFailuresOnlyMfaLevel1(_FailuresOnlyMfaCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides(MFA_ENABLED=1)


class TestFailuresOnlyRefreshLevel3(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = overrides(REFRESH_TOKEN_ENABLED=1)

    def test_successful_refreshes_do_not_consume(self):
        refresh_token = self.new_refresh_token()
        for _ in range(5):
            response = self.refresh(refresh_token)
            self.assertEqual(200, response.status_code)
            refresh_token = response.json["refresh_token"]

    def test_invalid_refresh_tokens_consume(self):
        responses = [self.refresh("not-a-valid-token") for _ in range(3)]
        self.assert_statuses([401] * 3, responses)
        self.assertEqual(429, self.refresh(self.new_refresh_token()).status_code)

    def test_revoked_refresh_tokens_consume(self):
        revoked = self.new_refresh_token()
        self.assertEqual(200, self.logout(revoked).status_code)
        responses = [self.refresh(revoked) for _ in range(3)]
        self.assert_statuses([401] * 3, responses)
        self.assertEqual(429, self.refresh(self.new_refresh_token()).status_code)

    def test_refresh_counter_is_separate_from_login(self):
        self.assert_statuses([400] * 3, [self.bad_login() for _ in range(3)])
        self.assertEqual(200, self.refresh(self.new_refresh_token()).status_code)

    def test_refresh_without_token_consumes(self):
        responses = [self.post(REFRESH_URL, {}) for _ in range(3)]
        self.assert_statuses([400] * 3, responses)
        self.assertEqual(429, self.refresh(self.new_refresh_token()).status_code)

    def test_canonical_and_legacy_refresh_routes_share_the_counter(self):
        responses = [
            self.refresh("not-a-valid-token", url=REFRESH_URL),
            self.refresh("not-a-valid-token", url=LEGACY_REFRESH_URL),
            self.refresh("not-a-valid-token", url=REFRESH_URL),
        ]
        self.assert_statuses([401] * 3, responses)
        response = self.refresh(self.new_refresh_token(), url=LEGACY_REFRESH_URL)
        self.assertEqual(429, response.status_code)

    def test_logout_never_consumes(self):
        responses = [self.logout("not-a-valid-token") for _ in range(20)]
        self.assert_statuses([200] * 20, responses)
        responses = [
            self.logout("not-a-valid-token", url=LEGACY_LOGOUT_URL) for _ in range(20)
        ]
        self.assert_statuses([200] * 20, responses)


class TestFailuresOnlyRefreshLevel1(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides()

    def test_invalid_refresh_tokens_consume_level_1(self):
        responses = [self.refresh("not-a-valid-token") for _ in range(3)]
        self.assert_statuses([401] * 3, responses)
        self.assertEqual(429, self.refresh("not-a-valid-token").status_code)


class TestFailuresOnlyOpenAuth(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides(
        AUTH_TYPE=AUTH_OID,
        OID_PROVIDER="https://test-provider.example.com",
        OID_EXPECTED_AUDIENCE="test-audience-id",
    )

    DECODE = "cornflow.shared.authentication.Auth.decode_token"

    def setUp(self):
        super().setUp()
        self.make_user("testname", "testname@test.org", SERVICE_PASSWORD, SERVICE_ROLE)

    def token_login(self, token="valid_token", ip=IP1, url=LOGIN_URL):
        return self.post(
            url, {}, ip=ip, headers={"Authorization": f"Bearer {token}"}
        )

    def test_successful_token_logins_do_not_consume(self):
        with mock.patch(self.DECODE, return_value={"sub": "testname"}):
            responses = [self.token_login() for _ in range(20)]
        self.assert_statuses([200] * 20, responses)

    def test_failed_token_logins_consume(self):
        responses = [self.token_login("invalid_token") for _ in range(3)]
        self.assert_statuses([401] * 3, responses)
        with mock.patch(self.DECODE, return_value={"sub": "testname"}):
            self.assertEqual(429, self.token_login().status_code)

    def test_missing_header_consumes(self):
        responses = [self.post(LOGIN_URL, {}) for _ in range(3)]
        self.assert_statuses([400] * 3, responses)
        with mock.patch(self.DECODE, return_value={"sub": "testname"}):
            self.assertEqual(429, self.token_login().status_code)

    def test_legacy_route_shares_the_counter(self):
        with mock.patch(self.DECODE, return_value={"sub": "testname"}):
            for _ in range(10):
                self.assertEqual(200, self.token_login(url=LEGACY_LOGIN_URL).status_code)
        responses = [
            self.token_login("invalid_token", url=LEGACY_LOGIN_URL),
            self.token_login("invalid_token", url=LOGIN_URL),
            self.token_login("invalid_token", url=LEGACY_LOGIN_URL),
        ]
        self.assert_statuses([401] * 3, responses)
        with mock.patch(self.DECODE, return_value={"sub": "testname"}):
            self.assertEqual(429, self.token_login().status_code)


class TestFailuresOnlyLdap(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides(AUTH_TYPE=AUTH_LDAP)

    AUTHENTICATE = (
        "cornflow.endpoints.login.LoginBaseEndpoint.auth_ldap_authenticate"
    )

    def ldap_login(self):
        return self.login("ana", USER_PASSWORD)

    def test_successful_ldap_logins_do_not_consume(self):
        db.session.expire_all()
        ana = UserModel.get_one_user_by_username("ana")
        with mock.patch(self.AUTHENTICATE, return_value=ana):
            responses = [self.ldap_login() for _ in range(20)]
        self.assert_statuses([200] * 20, responses)

    def test_failed_ldap_logins_consume(self):
        with mock.patch(self.AUTHENTICATE, side_effect=InvalidCredentials()):
            responses = [self.ldap_login() for _ in range(3)]
        self.assert_statuses([400] * 3, responses)
        ana = UserModel.get_one_user_by_username("ana")
        with mock.patch(self.AUTHENTICATE, return_value=ana):
            self.assertEqual(429, self.ldap_login().status_code)


class TestRecoverCountsEveryRequest(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides(
        SERVICE_EMAIL_ADDRESS="cornflow@test.com",
        SERVICE_EMAIL_PASSWORD="not-used",
        SERVICE_EMAIL_SERVER="smtp.test.com",
        SERVICE_EMAIL_PORT=465,
    )

    SEND_EMAIL = "cornflow.endpoints.user.send_email_to"

    def recover(self, email, ip=IP1):
        return self.put(RECOVER_PASSWORD_URL, {"email": email}, ip=ip)

    def test_recover_counts_successful_requests(self):
        with mock.patch(self.SEND_EMAIL):
            responses = [self.recover("nobody@test.org") for _ in range(3)]
        self.assert_statuses([200, 200, 429], responses)
        self.assert_rate_limited(responses[2])

    def test_recover_counts_existing_and_unknown_alike(self):
        with mock.patch(self.SEND_EMAIL):
            known = [self.recover("ana@test.org", ip=IP1) for _ in range(3)]
            unknown = [self.recover("nobody@test.org", ip=IP2) for _ in range(3)]
        self.assert_statuses([200, 200, 429], known)
        self.assert_statuses([200, 200, 429], unknown)
        self.assertEqual(known[0].json, unknown[0].json)
        self.assertEqual(known[1].json, unknown[1].json)

    def test_reset_counts_successful_requests(self):
        passwords = ["Plume-Orbit-Cactus8", "Velvet&Granite#42q", "Harbor!Lynx-Quartz7"]
        responses = []
        for password in passwords:
            token = Auth.generate_token(self.ana.id, purpose=TOKEN_PURPOSE_PWD_RESET)
            responses.append(
                self.put(
                    RESET_PASSWORD_URL,
                    {"password": password},
                    headers={"Authorization": f"Bearer {token}"},
                )
            )
        self.assert_statuses([200, 200, 429], responses)


class TestFailuresOnlyDisabled(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    # RATELIMIT_ENABLED is left to the helper default (0)
    config_overrides = {"RATELIMIT_LOGIN": "3 per minute"}

    def test_disabled_limiter_never_answers_429(self):
        responses = [self.bad_login() for _ in range(10)]
        responses += [self.refresh("not-a-valid-token") for _ in range(10)]
        for response in responses:
            self.assertNotEqual(429, response.status_code)


class TestFailuresOnlyTrustedProxy(_RateLimitBase, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = overrides(RATELIMIT_TRUST_FORWARDED_FOR=1)

    def test_forwarded_ip_is_counted_when_trusted(self):
        header = {"X-Forwarded-For": "10.0.0.1"}
        self.assert_statuses(
            [400] * 3, [self.bad_login(headers=header) for _ in range(3)]
        )
        self.assertEqual(429, self.good_login(headers=header).status_code)
        self.assertEqual(
            200, self.good_login(headers={"X-Forwarded-For": "10.0.0.2"}).status_code
        )

    def test_client_set_forwarded_entries_are_ignored(self):
        # The proxy appends the address it sees on the right; whatever the
        # client sends on the left must not give it a fresh counter
        responses = [
            self.bad_login(headers={"X-Forwarded-For": f"198.51.100.{i}, 10.0.0.1"})
            for i in range(3)
        ]
        self.assert_statuses([400] * 3, responses)
        response = self.good_login(
            headers={"X-Forwarded-For": "198.51.100.99, 10.0.0.1"}
        )
        self.assertEqual(429, response.status_code)

    def test_audit_records_the_proxy_reported_ip(self):
        with self.assertLogs("cornflow.audit", level="INFO") as logs:
            self.bad_login(headers={"X-Forwarded-For": "198.51.100.7, 10.0.0.1"})
        ips = {json.loads(record.getMessage()).get("ip") for record in logs.records}
        self.assertEqual({"10.0.0.1"}, ips)

    def test_successes_behind_proxy_do_not_consume(self):
        header = {"X-Forwarded-For": "10.0.0.1"}
        responses = [self.good_login(headers=header) for _ in range(20)]
        self.assert_statuses([200] * 20, responses)


if __name__ == "__main__":
    unittest.main()
