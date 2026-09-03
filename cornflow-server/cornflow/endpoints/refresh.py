"""
Endpoints for the refresh-token session flow (ENS op.acc — session
management).

- ``POST /token/refresh/`` exchanges a valid refresh token for a fresh access
  + refresh token pair, sliding the inactivity window and rotating the refresh
  token. It enforces the inactivity timeout, the absolute session cap, global
  revocation and refresh-token reuse detection.
- ``POST /logout/`` revokes the session behind a refresh token.

Both take the refresh token in the JSON body (``{"refresh_token": "..."}``)
and validate it themselves, so — like login — they are registered outside the
permission system and carry no ``@authenticate`` decorator.
"""

from flask import request
from flask_apispec import doc

from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.shared.audit import audit
from cornflow.shared.authentication import Auth
from cornflow.shared.rate_limit import (
    limiter,
    login_rate_limit,
    RATE_LIMIT_MESSAGE,
)


class RefreshTokenEndpoint(BaseMetaResource):
    """Endpoint to renew a session by exchanging the refresh token."""

    # Same per-IP limit as the login endpoint: both are unauthenticated
    # endpoints that take a credential in the body
    decorators = [limiter.limit(login_rate_limit, error_message=RATE_LIMIT_MESSAGE)]

    def __init__(self):
        super().__init__()
        self.auth_class = Auth

    @doc(description="Refresh a session token", tags=["Users"])
    def post(self):
        """
        API (POST) method to obtain a new access + refresh token pair from a
        valid refresh token.

        :return: a dict with the new ``token``, ``refresh_token`` and user
          ``id``, and the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        body = request.get_json(silent=True) or {}
        # The session.refreshed audit event is emitted by the auth layer, which
        # is where the user behind the token is resolved
        result = self.auth_class.consume_refresh_token(body.get("refresh_token"))
        return result, 200


class LogoutEndpoint(BaseMetaResource):
    """Endpoint to revoke the session behind a refresh token."""

    decorators = [limiter.limit(login_rate_limit, error_message=RATE_LIMIT_MESSAGE)]

    def __init__(self):
        super().__init__()
        self.auth_class = Auth

    @doc(description="Log out (revoke the refresh-token session)", tags=["Users"])
    def post(self):
        """
        API (POST) method to close a session. Idempotent: an invalid, expired
        or already-revoked refresh token still returns success.

        :return: a message and the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        body = request.get_json(silent=True) or {}
        user = self.auth_class.revoke_session(body.get("refresh_token"))
        # A logout carries no session credential, so the actor is taken from
        # the session that was closed (None when there was nothing to close)
        audit(
            "session.logout",
            actor_id=getattr(user, "id", None),
            actor=getattr(user, "username", None),
        )
        return {"message": "The session has been closed"}, 200
