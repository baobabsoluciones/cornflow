"""
Endpoint to manage the personal API key of a user: a long-lived bearer
token (an alternative to the session JWT) meant for automation. It is minted
behind full authentication (a valid session, plus a fresh TOTP step-up when
the user has MFA enabled) and only ever a single key is active per user:
generating a new one revokes the previous one. The key is shown only once.

Generation is available:
- from the web client / API, on a full session (this endpoint),
- from the CLI (``cornflow users api_key``), which is trusted by machine
  access.

It can be disabled per deployment with PERSONAL_TOKEN_ENABLED=0.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app, g
from flask_apispec import doc, marshal_with, use_kwargs

from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import UserModel
from cornflow.schemas.user import ApiKeyRequest, ApiKeyResponse
from cornflow.shared.audit import audit
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ALL_DEFAULT_ROLES, TOKEN_TYPE_API_KEY
from cornflow.shared.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    NoPermission,
)


class UserApiKeyEndpoint(BaseMetaResource):
    """
    Endpoint to generate (POST) or revoke (DELETE) the personal API key of
    the authenticated user.
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth

    def _check_enabled(self):
        if int(current_app.config.get("PERSONAL_TOKEN_ENABLED", 1)) != 1:
            raise EndpointNotImplemented(
                "Personal API key generation is disabled on this deployment",
                log_txt="Error while a user tries to use a personal API key. "
                "The feature is disabled (PERSONAL_TOKEN_ENABLED=0).",
            )

    def _require_full_session(self):
        # An API key must not be able to mint or revoke API keys (a leaked
        # key could otherwise perpetuate itself). This action needs a real
        # interactive session.
        if getattr(g, "token_type", None) == TOKEN_TYPE_API_KEY:
            raise NoPermission(
                error="This action requires an interactive session and can "
                "not be performed with an API key",
                log_txt="Error while a user tries to manage an API key using "
                "an API key.",
            )

    @doc(description="Generate a personal API key", tags=["Users"])
    @authenticate(auth_class=Auth())
    @use_kwargs(ApiKeyRequest, location="json")
    @marshal_with(ApiKeyResponse)
    def post(self, **kwargs):
        """
        API (POST) method to generate a personal API key. Requires a full
        session; when the user has MFA enabled and API_KEY_STEPUP_TOTP is on,
        a fresh TOTP code must be provided. Generating a new key revokes the
        previous one, and the key is returned only once.

        :return: a dict with the api_key and its expiry, and the HTTP status
        :rtype: Tuple(dict, integer)
        """
        self._check_enabled()
        self._require_full_session()
        user = self.get_user()

        step_up = int(current_app.config.get("API_KEY_STEPUP_TOTP", 1)) == 1
        if user.mfa_enabled and step_up:
            totp_code = kwargs.get("totp_code")
            if not totp_code or not user.check_totp_code(totp_code):
                raise InvalidCredentials(
                    "A valid two-factor authentication code is required to "
                    "generate an API key",
                    log_txt=f"Error while user {user.id} tries to generate an "
                    f"API key. The step-up TOTP code is missing or invalid.",
                )

        user.rotate_api_key()
        api_key = self.auth_class.generate_api_key(user.id)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=int(current_app.config["API_KEY_DURATION_DAYS"])
        )
        current_app.logger.info(f"User {user.id} generated a personal API key")
        audit(
            "apikey.issued",
            actor_id=user.id,
            actor=user.username,
            source="ui",
            expires_at=expires_at,
        )
        return {"api_key": api_key, "expires_at": expires_at}, 201

    @doc(description="Revoke the personal API key", tags=["Users"])
    @authenticate(auth_class=Auth())
    def delete(self):
        """
        API (DELETE) method to revoke the user's personal API key.

        :return: a message and the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        self._check_enabled()
        self._require_full_session()
        user = self.get_user()
        user.revoke_api_keys()
        current_app.logger.info(f"User {user.id} revoked their personal API key")
        audit("apikey.revoked", actor_id=user.id, actor=user.username, source="ui")
        return {"message": "The API key has been revoked"}, 200
