"""
Unit tests for the refresh-token handling of the raw client: storing the
tokens on login, the transparent renew-and-retry on a 401, and logout.
All network calls are mocked.
"""

from unittest import TestCase, mock

from cornflow_client.raw_cornflow_client import CornFlowApiError, RawCornFlow


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

    def test_failed_refresh_returns_the_original_401(self):
        self.login({"token": "access-1", "refresh_token": "refresh-1", "id": 1})
        with mock.patch(
            "cornflow_client.raw_cornflow_client.requests.request",
            return_value=_response(401, {"error": "expired"}),
        ) as req, mock.patch(
            "cornflow_client.raw_cornflow_client.requests.post",
            return_value=_response(401, {"error": "session revoked"}),
        ):
            response = self.client.get_all_instances()
        self.assertEqual(401, response.status_code)
        # no retry after the failed refresh
        self.assertEqual(1, req.call_count)

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
