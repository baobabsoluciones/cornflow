"""
Unit tests for the refresh-token handling of the raw client: storing the
tokens on login, the transparent renew-and-retry on a 401, and logout,
and the clear error when the server refuses to renew the session.
All network calls are mocked.
"""

from unittest import TestCase, mock

from cornflow_client.cornflow_client import CornFlow
from cornflow_client.raw_cornflow_client import (
    SESSION_CLOSED_MESSAGE,
    CornFlowApiError,
    RawCornFlow,
)

RAW = "cornflow_client.raw_cornflow_client"
LOGIN_BODY = {"token": "access-1", "refresh_token": "refresh-1", "id": 1}


def _response(status_code, body):
    response = mock.MagicMock()
    response.status_code = status_code
    response.json.return_value = body
    return response


class TestRawClientRefresh(TestCase):
    def setUp(self):
        self.client = RawCornFlow(url="http://cornflow.test/")

    def login(self, body):
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(200, body),
        ):
            return self.client.login("someuser", "somepassword")

    def test_login_stores_access_and_refresh_tokens(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        self.assertEqual("access-1", self.client.token)
        self.assertEqual("refresh-1", self.client.refresh_token)

    def test_login_without_refresh_token(self):
        # service users / refresh-disabled deployments return a single token
        self.login({"token": "access-1", "id": 1})
        self.assertEqual("access-1", self.client.token)
        self.assertIsNone(self.client.refresh_token)

    def test_refresh_rotates_the_tokens(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(
                200, {"token": "access-2", "refresh_token": "refresh-2", "id": 1}
            ),
        ) as post:
            self.client.refresh()
        self.assertEqual(
            "http://cornflow.test/token/refresh/", post.call_args[0][0]
        )
        self.assertEqual(
            {"refresh_token": "refresh-1"}, post.call_args[1]["json"]
        )
        self.assertEqual("access-2", self.client.token)
        self.assertEqual("refresh-2", self.client.refresh_token)

    def test_refresh_without_refresh_token_raises(self):
        self.client.token = "an-api-key"
        with self.assertRaises(CornFlowApiError):
            self.client.refresh()

    def test_expired_access_token_is_renewed_and_the_call_retried(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.request",
            side_effect=[
                _response(401, {"error": "expired"}),
                _response(200, [{"id": "instance-1"}]),
            ],
        ) as req, mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(
                200, {"token": "access-2", "refresh_token": "refresh-2", "id": 1}
            ),
        ):
            response = self.client.get_all_instances()
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, req.call_count)
        # the retried call used the renewed access token
        retry_headers = req.call_args[1]["headers"]
        self.assertEqual("Bearer access-2", retry_headers["Authorization"])

    def test_expired_token_reported_as_400_is_also_renewed(self):
        # UAT 12.5: the server used to answer 400 (not 401) when the access
        # token expired, so a retry that only looked at 401 never fired and the
        # script died after ~15 minutes. Servers that still do must work.
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.request",
            side_effect=[
                _response(400, {"error": "The token has expired, please login again"}),
                _response(200, [{"id": "instance-1"}]),
            ],
        ) as req, mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(
                200, {"token": "access-2", "refresh_token": "refresh-2", "id": 1}
            ),
        ):
            response = self.client.get_all_instances()
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, req.call_count)

    def test_an_ordinary_400_is_not_retried(self):
        # only an expiry justifies renewing: a plain bad request must surface
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.request",
            return_value=_response(400, {"error": "Invalid payload"}),
        ) as req:
            response = self.client.get_all_instances()
        self.assertEqual(400, response.status_code)
        self.assertEqual(1, req.call_count)

    def test_401_without_refresh_token_is_returned_as_is(self):
        # API-key style session: no refresh token, the 401 is not retried
        self.client.set_api_key("an-api-key")
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.request",
            return_value=_response(401, {"error": "revoked"}),
        ) as req:
            response = self.client.get_all_instances()
        self.assertEqual(401, response.status_code)
        self.assertEqual(1, req.call_count)

    def test_refresh_rejected_with_401_raises_session_closed_error(self):
        self.login(LOGIN_BODY)
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(
                401, {"error": "The token has expired, please login again"}
            ),
        ) as req, mock.patch(
            RAW + ".requests.post",
            return_value=_response(
                401, {"error": "The session has expired, please log in again"}
            ),
        ) as post:
            with self.assertRaises(CornFlowApiError) as ctx:
                self.client.get_all_instances()
        self.assertEqual(SESSION_CLOSED_MESSAGE, str(ctx.exception))
        # no retry after the rejected refresh
        self.assertEqual(1, req.call_count)
        self.assertEqual(1, post.call_count)
        self.assertEqual("http://cornflow.test/token/refresh/", post.call_args[0][0])

    def test_session_closed_message_content(self):
        self.assertEqual(
            "The session has been closed (inactivity or maximum session length). "
            "Log in again; for unattended processes use a personal API key "
            "(set_api_key, or CORNFLOW_SERVICE_API_KEY in Airflow).",
            SESSION_CLOSED_MESSAGE,
        )
        for text in (
            "session has been closed",
            "inactivity",
            "maximum session length",
            "Log in again",
            "API key",
            "set_api_key",
            "CORNFLOW_SERVICE_API_KEY",
        ):
            self.assertIn(text, SESSION_CLOSED_MESSAGE)

    def test_legacy_400_then_refresh_401_raises_session_closed_error(self):
        self.login(LOGIN_BODY)
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(
                400, {"error": "The token has expired, please login again"}
            ),
        ) as req, mock.patch(
            RAW + ".requests.post",
            return_value=_response(401, {"error": "session closed"}),
        ):
            with self.assertRaises(CornFlowApiError) as ctx:
                self.client.get_all_instances()
        self.assertEqual(SESSION_CLOSED_MESSAGE, str(ctx.exception))
        self.assertEqual(1, req.call_count)

    def test_refresh_failing_for_other_reasons_returns_the_original_response(self):
        for status in (400, 403, 429, 500, 503):
            with self.subTest(refresh_status=status):
                self.login(LOGIN_BODY)
                original = _response(401, {"error": "expired"})
                with mock.patch(
                    RAW + ".requests.request", return_value=original
                ) as req, mock.patch(
                    RAW + ".requests.post",
                    return_value=_response(status, {"error": "refresh failed"}),
                ):
                    response = self.client.get_all_instances()
                self.assertIs(original, response)
                self.assertEqual(401, response.status_code)
                self.assertEqual(1, req.call_count)
                self.assertEqual("access-1", self.client.token)
                self.assertEqual("refresh-1", self.client.refresh_token)

    def test_api_key_session_never_refreshes(self):
        self.client.set_api_key("an-api-key")
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(401, {"error": "revoked"}),
        ), mock.patch(RAW + ".requests.post") as post:
            response = self.client.get_all_instances()
        self.assertEqual(401, response.status_code)
        post.assert_not_called()

    def test_login_without_refresh_token_returns_the_401(self):
        # levels 1 and 2 and service users get no refresh token
        self.login({"token": "access-1", "id": 1})
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(401, {"error": "expired"}),
        ) as req, mock.patch(RAW + ".requests.post") as post:
            response = self.client.get_all_instances()
        self.assertEqual(401, response.status_code)
        self.assertEqual(1, req.call_count)
        post.assert_not_called()

    def test_nested_call_refreshes_once_and_raises(self):
        self.login(LOGIN_BODY)
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(401, {"error": "expired"}),
        ) as req, mock.patch(
            RAW + ".requests.post",
            return_value=_response(401, {"error": "session closed"}),
        ) as post:
            with self.assertRaises(CornFlowApiError) as ctx:
                self.client.get_data("exec-1")
        self.assertEqual(SESSION_CLOSED_MESSAGE, str(ctx.exception))
        self.assertEqual(1, post.call_count)
        self.assertEqual(1, req.call_count)

    def test_closed_session_keeps_the_stored_tokens(self):
        self.login(LOGIN_BODY)
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(401, {"error": "expired"}),
        ), mock.patch(
            RAW + ".requests.post",
            return_value=_response(401, {"error": "session closed"}),
        ):
            with self.assertRaises(CornFlowApiError):
                self.client.get_all_instances()
        self.assertEqual("access-1", self.client.token)
        self.assertEqual("refresh-1", self.client.refresh_token)

    def test_high_level_client_raises_session_closed_error(self):
        client = CornFlow(url="http://cornflow.test/")
        with mock.patch(
            RAW + ".requests.post", return_value=_response(200, LOGIN_BODY)
        ):
            client.login("someuser", "somepassword")
        with mock.patch(
            RAW + ".requests.request",
            return_value=_response(401, {"error": "expired"}),
        ), mock.patch(
            RAW + ".requests.post",
            return_value=_response(401, {"error": "session closed"}),
        ):
            with self.assertRaises(CornFlowApiError) as ctx:
                client.get_all_instances()
        self.assertEqual(SESSION_CLOSED_MESSAGE, str(ctx.exception))
        self.assertFalse(str(ctx.exception).startswith("Expected a code"))

    def test_high_level_client_retries_after_successful_refresh(self):
        client = CornFlow(url="http://cornflow.test/")
        with mock.patch(
            RAW + ".requests.post", return_value=_response(200, LOGIN_BODY)
        ):
            client.login("someuser", "somepassword")
        with mock.patch(
            RAW + ".requests.request",
            side_effect=[
                _response(401, {"error": "expired"}),
                _response(200, [{"id": "instance-1"}]),
            ],
        ), mock.patch(
            RAW + ".requests.post",
            return_value=_response(
                200, {"token": "access-2", "refresh_token": "refresh-2", "id": 1}
            ),
        ):
            result = client.get_all_instances()
        self.assertEqual([{"id": "instance-1"}], result)

    def test_logout_revokes_and_clears(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(200, {"message": "closed"}),
        ) as post:
            self.client.logout()
        self.assertEqual("http://cornflow.test/logout/", post.call_args[0][0])
        self.assertIsNone(self.client.token)
        self.assertIsNone(self.client.refresh_token)

    def test_set_api_key_clears_the_refresh_token(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        self.client.set_api_key("an-api-key")
        self.assertEqual("an-api-key", self.client.token)
        self.assertIsNone(self.client.refresh_token)
