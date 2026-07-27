"""
This file contains the auth class that can be used for authentication on the request to the REST API
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Tuple

# Imports from external libraries
import jwt
import requests
from cachetools import TTLCache
from flask import request, g, current_app, Request
from jwt.algorithms import RSAAlgorithm
from werkzeug.datastructures import Headers

# Imports from internal modules
from cornflow.models import (
    PermissionsDAG,
    PermissionViewRoleModel,
    SessionModel,
    UserModel,
    ViewModel,
)
from cornflow.shared.const import (
    API_KEY_FORBIDDEN_ENDPOINTS,
    AUTH_OID,
    PERMISSION_METHOD_MAP,
    INTERNAL_TOKEN_ISSUER,
    OID_PROVIDER_AZURE,
    PWD_ROTATION_ALLOWED_ENDPOINTS,
    TOKEN_PURPOSE_ALLOWED_ENDPOINTS,
    TOKEN_PURPOSE_MFA_SETUP,
    TOKEN_PURPOSE_PWD_RESET,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_API_KEY,
    TOKEN_TYPE_REFRESH,
)
from cornflow.shared.audit import audit
from cornflow.shared.exceptions import (
    CommunicationError,
    InvalidCredentials,
    InvalidData,
    InvalidUsage,
    NoPermission,
)

# Cache for storing public keys with 1 hour TTL
public_keys_cache = TTLCache(maxsize=10, ttl=3600)


class Auth:
    # BI tokens (BIAuth) are long-lived by design and skip the
    # token-version revocation check
    CHECK_TOKEN_VERSION = True

    def __init__(self, user_model=UserModel):
        self.user_model = user_model

    def authenticate(self):
        user, payload = self.get_user_and_payload_from_header(request.headers)
        token_type = payload.get("type") if isinstance(payload, dict) else None
        purpose = payload.get("purpose") if isinstance(payload, dict) else None
        if token_type == TOKEN_TYPE_REFRESH:
            # A refresh token is only valid at the refresh endpoint; it must
            # never grant access to a normal endpoint.
            raise InvalidCredentials(
                "A refresh token can not be used to access this endpoint",
                status_code=401,
                log_txt=f"Error while user {user.id} tries to authenticate with "
                f"a refresh token on endpoint {request.endpoint}.",
            )
        if token_type == TOKEN_TYPE_API_KEY:
            # Personal API key: validate its version and restrict it away from
            # the security-management surface (it is a data/automation
            # credential, not for account self-management)
            Auth._check_api_key(user, payload)
            Auth._check_api_key_access(user)
        elif purpose is not None:
            Auth._check_purpose_token_access(purpose, user)
        else:
            Auth._check_password_rotation(user)
        # Expose the token type so endpoints can require a full session for
        # sensitive actions (e.g. minting API keys)
        g.token_type = token_type
        Auth._get_permission_for_request(request, user.id)
        g.user = user
        return True

    @staticmethod
    def _check_api_key(user, payload):
        """
        Rejects a personal API key whose version no longer matches the user's
        current one (revoked by regeneration, explicit revoke, account lock
        or MFA reset).

        :param user: the user the key belongs to
        :param dict payload: the decoded token payload
        """
        if int(payload.get("akv", -1)) != int(user.api_key_version or 0):
            raise InvalidCredentials(
                "The API key has been revoked, please generate a new one",
                status_code=401,
                log_txt=f"Error while user {user.id} authenticates with an API "
                f"key. The key version is stale (revoked).",
            )

    @staticmethod
    def _check_api_key_access(user):
        """
        Blocks a personal API key from reaching the security-sensitive
        endpoints (password change, MFA, API key management, user/role
        administration). A leaked key must not be able to escalate.

        :param user: the user the key belongs to
        """
        endpoint = request.endpoint
        forbidden_methods = API_KEY_FORBIDDEN_ENDPOINTS.get(endpoint, [])
        if request.method in forbidden_methods:
            raise NoPermission(
                error="This action requires an interactive session and can "
                "not be performed with an API key",
                status_code=403,
                payload={"error_code": "api_key_forbidden"},
                log_txt=f"Error while user {user.id} tries to access endpoint "
                f"{endpoint} ({request.method}) with an API key.",
            )

    @staticmethod
    def _check_purpose_token_access(purpose: str, user):
        """
        Tokens carrying a purpose claim are temporary tokens that can only be
        used on a restricted set of endpoints (e.g. the MFA enrollment ones
        or the password reset endpoint).

        :param str purpose: the purpose claim found on the token
        :param user: the user object the token belongs to
        """
        endpoint = request.endpoint
        if endpoint in TOKEN_PURPOSE_ALLOWED_ENDPOINTS.get(purpose, []):
            return
        raise InvalidCredentials(
            "The provided token can only be used for its intended "
            "purpose and has no access to this endpoint",
            status_code=403,
            payload={"error_code": "purpose_token"},
            log_txt=f"Error while user {user.id} tries to access endpoint "
            f"{endpoint} with a temporary token with purpose {purpose}.",
        )

    @staticmethod
    def _check_password_rotation(user):
        """
        When password rotation is enforced, users whose password has expired
        or is flagged for a forced change can only access the endpoints
        needed to review their profile and set a new password.

        :param user: the user object
        """
        if int(current_app.config.get("PWD_ROTATION_ENFORCE", 1)) != 1:
            return
        if user.comes_from_external_provider():
            return
        if not (
            user.pwd_change_required or Auth.password_rotation_expired(user)
        ):
            return
        if user.is_service_user():
            return
        endpoint = request.endpoint
        allowed_methods = PWD_ROTATION_ALLOWED_ENDPOINTS.get(endpoint, [])
        if request.method in allowed_methods:
            if endpoint != "user-detail":
                return
            target_user_id = (request.view_args or {}).get("user_id")
            if target_user_id == user.id:
                return
        raise NoPermission(
            error="Your password has expired or must be renewed. "
            "Please change your password before continuing.",
            status_code=403,
            payload={"error_code": "password_rotation"},
            log_txt=f"Error while user {user.id} tries to access endpoint "
            f"{endpoint}. The user's password has expired and rotation "
            f"is enforced.",
        )

    @staticmethod
    def password_rotation_expired(user) -> bool:
        """
        Checks if the user's password is older than the rotation period
        defined by the PWD_ROTATION_TIME config (in days).

        :param user: the user object
        :return: True if the password has expired
        :rtype: bool
        """
        if not user.pwd_last_change:
            return False
        if isinstance(user.pwd_last_change, datetime):
            if user.pwd_last_change.tzinfo is None:
                last_change = user.pwd_last_change.replace(tzinfo=timezone.utc)
            else:
                last_change = user.pwd_last_change
        else:
            last_change = datetime.fromtimestamp(user.pwd_last_change, timezone.utc)

        expiration_time = last_change + timedelta(
            days=int(current_app.config["PWD_ROTATION_TIME"])
        )
        return expiration_time < datetime.now(timezone.utc)

    @staticmethod
    def dag_permission_required(func):
        """
        DAG permission decorator
        :param func:
        :return:
        """

        @wraps(func)
        def dag_decorator(*args, **kwargs):
            if int(current_app.config["OPEN_DEPLOYMENT"]) == 0:
                user_id = g.user.id
                dag_id = request.json.get("schema", None)
                if dag_id is None:
                    raise InvalidData(
                        error="The request does not specify a schema to use",
                        status_code=400,
                        log_txt=f"Error while user {g.user} tries to access a dag. "
                        f"The schema is not specified in the request.",
                    )
                else:
                    if PermissionsDAG.check_if_has_permissions(user_id, dag_id):
                        # We have permissions
                        return func(*args, **kwargs)
                    else:
                        raise NoPermission(
                            error="You do not have permission to use this DAG",
                            status_code=403,
                            log_txt=f"Error while user {g.user} tries to access dag {dag_id}. "
                            f"The user does not have permission to access the dag.",
                        )
            else:
                return func(*args, **kwargs)

        return dag_decorator

    @staticmethod
    def generate_token(user_id: int = None, purpose: str = None) -> str:
        """
        Generates a token given a user_id. The token will contain the username in the sub claim.

        :param int user_id: user id to generate the token for
        :param str purpose: optional purpose claim for temporary restricted
          tokens (e.g. the MFA enrollment token issued during login). Tokens
          with a purpose are short-lived and only valid on specific endpoints.
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        user = UserModel.get_one_user(user_id)
        if user is None:
            err = "User does not exist"
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        payload = {
            "exp": datetime.now(timezone.utc)
            + timedelta(hours=float(current_app.config["TOKEN_DURATION"])),
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
            # Token version: bumped on security events (password change,
            # account lock, MFA reset) to revoke outstanding sessions
            "tv": user.token_version or 0,
        }

        if purpose is not None:
            purpose_durations = {
                TOKEN_PURPOSE_MFA_SETUP: int(
                    current_app.config.get("MFA_SETUP_TOKEN_DURATION_MINUTES", 10)
                ),
                TOKEN_PURPOSE_PWD_RESET: int(
                    current_app.config.get("PWD_RESET_TOKEN_DURATION_MINUTES", 30)
                ),
            }
            payload["purpose"] = purpose
            payload["exp"] = datetime.now(timezone.utc) + timedelta(
                minutes=purpose_durations.get(purpose, 10)
            )

        return jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

    @staticmethod
    def generate_access_token(user_id: int = None) -> str:
        """
        Generates a short-lived access token (ACCESS_TOKEN_DURATION_MINUTES)
        carrying the token-version claim. It is the credential sent on every
        request; the client renews it via the refresh endpoint.

        :param int user_id: user id to generate the token for
        :return: the generated access token
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate an access token. " + err
            )
        user = UserModel.get_one_user(user_id)
        if user is None:
            err = "User does not exist"
            raise InvalidUsage(
                err, log_txt="Error while trying to generate an access token. " + err
            )
        payload = {
            "exp": datetime.now(timezone.utc)
            + timedelta(
                minutes=int(current_app.config["ACCESS_TOKEN_DURATION_MINUTES"])
            ),
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
            "tv": user.token_version or 0,
            "type": TOKEN_TYPE_ACCESS,
        }
        return jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

    @staticmethod
    def generate_refresh_token(user_id: int, session) -> str:
        """
        Generates a refresh token bound to a stored session. Its absolute
        expiry equals the session's, and it carries the session id (``sid``)
        and the current refresh-token id (``jti``) so the server can rotate it
        and detect reuse.

        :param int user_id: user id to generate the token for
        :param session: the :class:`SessionModel` the token belongs to
        :return: the generated refresh token
        :rtype: str
        """
        user = UserModel.get_one_user(user_id)
        if user is None:
            err = "User does not exist"
            raise InvalidUsage(
                err, log_txt="Error while trying to generate a refresh token. " + err
            )
        payload = {
            "exp": session.expires_at,
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
            "tv": user.token_version or 0,
            "type": TOKEN_TYPE_REFRESH,
            "sid": session.session_id,
            "jti": session.jti,
        }
        return jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

    @staticmethod
    def issue_session_tokens(user) -> dict:
        """
        Issues the tokens returned on a successful interactive login/enrollment.

        When refresh-token sessions are enabled and the user is interactive, a
        stateful session is created and a short access token plus a refresh
        token are returned. Service users (and deployments with the feature
        disabled) keep a single long-lived token — automation should use API
        keys, not refresh tokens.

        :param user: the authenticated user
        :return: a dict with ``token`` and, when applicable, ``refresh_token``
        :rtype: dict
        """
        if (
            int(current_app.config.get("REFRESH_TOKEN_ENABLED", 1)) != 1
            or user.is_service_user()
        ):
            return {"token": Auth.generate_token(user.id)}
        session = SessionModel.create_for_user(user)
        return {
            "token": Auth.generate_access_token(user.id),
            "refresh_token": Auth.generate_refresh_token(user.id, session),
        }

    @staticmethod
    def consume_refresh_token(refresh_token: str) -> dict:
        """
        Validates a refresh token and, on success, rotates the session and
        returns a fresh access + refresh token pair. Enforces global
        revocation (token version), the sliding inactivity window, the
        absolute session cap and refresh-token reuse detection.

        :param str refresh_token: the refresh token presented by the client
        :return: a dict with ``token``, ``refresh_token`` and ``id``
        :rtype: dict
        """
        if not refresh_token:
            raise InvalidCredentials(
                "A refresh token is required",
                status_code=400,
                log_txt="Error while refreshing a session. The refresh token "
                "is missing.",
            )
        payload = Auth.decode_token(refresh_token)
        if not isinstance(payload, dict) or payload.get("type") != TOKEN_TYPE_REFRESH:
            raise InvalidCredentials(
                "Invalid refresh token",
                status_code=401,
                log_txt="Error while refreshing a session. The token is not a "
                "refresh token.",
            )
        user = UserModel.get_one_object(username=payload.get("sub"))
        if user is None:
            raise InvalidCredentials(
                "Invalid refresh token",
                status_code=401,
                log_txt="Error while refreshing a session. The user does not "
                "exist.",
            )
        if int(payload.get("tv", 0)) != int(user.token_version or 0):
            raise InvalidCredentials(
                "The session has been revoked, please log in again",
                status_code=401,
                log_txt=f"Error while user {user.id} refreshes a session. The "
                f"token version is stale (revoked).",
            )
        session = SessionModel.get_active(payload.get("sid"))
        if session is None:
            raise InvalidCredentials(
                "The session is no longer valid, please log in again",
                status_code=401,
                log_txt=f"Error while user {user.id} refreshes a session. The "
                f"session does not exist or is revoked.",
            )
        if payload.get("jti") != session.jti:
            # An already-rotated refresh token is being reused: treat it as a
            # theft signal and kill the whole session.
            session.revoke()
            audit(
                "session.reuse_detected",
                outcome="revoked",
                actor_id=user.id,
                actor=user.username,
                session_id=session.session_id,
            )
            raise InvalidCredentials(
                "The session has been revoked, please log in again",
                status_code=401,
                log_txt=f"Error while user {user.id} refreshes a session. A "
                f"superseded refresh token was reused; session revoked.",
            )
        if session.is_expired() or session.is_inactive():
            session.revoke()
            raise InvalidCredentials(
                "The session has expired, please log in again",
                status_code=401,
                log_txt=f"Error while user {user.id} refreshes a session. The "
                f"session expired (inactivity or absolute cap).",
            )
        session.rotate()
        return {
            "token": Auth.generate_access_token(user.id),
            "refresh_token": Auth.generate_refresh_token(user.id, session),
            "id": user.id,
        }

    @staticmethod
    def revoke_session(refresh_token: str):
        """
        Revokes the session behind a refresh token (logout). Idempotent: an
        invalid, expired or already-revoked token is a no-op.

        :param str refresh_token: the refresh token whose session to revoke
        """
        if not refresh_token:
            return
        try:
            payload = Auth.decode_token(refresh_token)
        except InvalidCredentials:
            return
        if not isinstance(payload, dict) or payload.get("type") != TOKEN_TYPE_REFRESH:
            return
        session = SessionModel.get_active(payload.get("sid"))
        if session is not None:
            session.revoke()

    @staticmethod
    def generate_api_key(user_id: int = None) -> str:
        """
        Generates a personal API key for a user: a long-lived bearer token
        (API_KEY_DURATION_DAYS) that is an alternative to the session JWT.
        The caller must bump the user's api_key_version first (rotate_api_key)
        so previously issued keys are revoked; this method signs a key with
        the current version.

        :param int user_id: user id to generate the key for
        :return: the generated API key
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the API key is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate an API key. " + err
            )

        user = UserModel.get_one_user(user_id)
        if user is None:
            err = "User does not exist"
            raise InvalidUsage(
                err, log_txt="Error while trying to generate an API key. " + err
            )

        payload = {
            "exp": datetime.now(timezone.utc)
            + timedelta(days=int(current_app.config["API_KEY_DURATION_DAYS"])),
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
            "type": TOKEN_TYPE_API_KEY,
            "akv": user.api_key_version or 0,
        }

        return jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

    @staticmethod
    def decode_token(token: str = None) -> dict:
        """
        Decodes a given JSON Web token and extracts the username from the sub claim.
        Works with both internal tokens and OpenID tokens by attempting verification methods sequentially.

        :param str token: the given JSON Web Token
        :return: dictionary containing the username from the token's sub claim
        :rtype: dict
        """
        if token is None:
            raise InvalidCredentials(
                "Must provide a token in Authorization header",
                log_txt="Error while trying to decode token. Token is missing.",
                status_code=400,
            )

        try:
            # Attempt 1: Verify as an internal token (HS256)
            payload = jwt.decode(
                token, current_app.config["SECRET_TOKEN_KEY"], algorithms=["HS256"]
            )
            if payload.get("iss") != INTERNAL_TOKEN_ISSUER:
                raise jwt.InvalidIssuerError(
                    "Internal token issuer mismatch after verification"
                )
            return payload

        except jwt.ExpiredSignatureError:
            # Handle expiration specifically, could apply to either token type if caught here first
            raise InvalidCredentials(
                "The token has expired, please login again",
                log_txt="Error while trying to decode token. The token has expired.",
                status_code=400,
            )
        except (
            jwt.InvalidSignatureError,
            jwt.DecodeError,
            jwt.InvalidTokenError,
        ) as e_internal:
            # Internal verification failed (signature, format, etc.). Try OIDC if configured.
            if current_app.config["AUTH_TYPE"] == AUTH_OID:
                try:
                    # Attempt 2: Verify as an OIDC token (RS256) using the dedicated method
                    return Auth().verify_token(
                        token,
                        current_app.config["OID_PROVIDER"],
                        current_app.config["OID_EXPECTED_AUDIENCE"],
                    )
                except jwt.ExpiredSignatureError:
                    # OIDC token expired
                    raise InvalidCredentials(
                        "The token has expired, please login again",
                        log_txt="Error while trying to decode OIDC token. The token has expired.",
                        status_code=400,
                    )
                except (
                    jwt.InvalidTokenError,
                    InvalidCredentials,
                    CommunicationError,
                ) as e_oidc:
                    # OIDC verification failed (JWT format, signature, kid, audience, issuer, comms error)
                    # Log details for debugging but return a generic error to the client.
                    log_message = (
                        f"Error decoding token. Internal verification failed ({type(e_internal).__name__}). "
                        f"OIDC verification failed ({type(e_oidc).__name__}: {str(e_oidc)})."
                    )
                    current_app.logger.warning(log_message)
                    raise InvalidCredentials(
                        "Invalid token format, signature, or configuration",
                        log_txt=log_message,
                        status_code=400,
                    )
            else:
                # Internal verification failed, and OIDC is not configured
                log_message = (
                    f"Error decoding token. Internal verification failed ({type(e_internal).__name__}). "
                    f"OIDC is not configured."
                )
                current_app.logger.warning(log_message)
                raise InvalidCredentials(
                    "Invalid token format or signature",
                    log_txt=log_message,
                    status_code=400,
                )
        except Exception as e:
            # Catch any other unexpected errors during the process
            log_message = f"Unexpected error during token decoding: {str(e)}"
            current_app.logger.error(log_message)
            raise InvalidCredentials(
                "Could not decode or verify token due to an unexpected server error",
                log_txt=log_message,
                status_code=500,
            )

    def get_token_from_header(self, headers: Headers = None) -> str:
        """
        Extracts the token given on the request from the Authorization headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the extracted token
        :rtype: str
        """
        if headers is None:
            raise InvalidUsage(
                "Request headers are missing",
                log_txt="Error while trying to get a token from header. The header is invalid.",
                status_code=400,
            )

        if "Authorization" not in headers:
            raise InvalidCredentials(
                "Authorization header is missing",
                log_txt="Error while trying to get a token from header. The auth token is not available.",
                status_code=400,
            )

        auth_header = headers.get("Authorization")

        if not auth_header:
            return ""

        if not auth_header.startswith("Bearer "):
            err = "Invalid Authorization header format. Must be 'Bearer <token>'"
            raise InvalidCredentials(
                err,
                log_txt=f"Error while trying to get a token from header. " + err,
                status_code=400,
            )

        try:
            token = auth_header.split(" ")[1]
            return token
        except Exception as e:
            err = "Invalid Authorization header format. Must be 'Bearer <token>'"
            raise InvalidCredentials(
                err,
                log_txt=f"Error while trying to get a token from header. " + err,
                status_code=400,
            )

    def get_user_and_payload_from_header(
        self, headers: Headers = None
    ) -> Tuple[UserModel, dict]:
        """
        Extracts the user and the decoded token payload from the
        Authorization headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the user object and the token payload
        :rtype: Tuple[:class:`UserModel`, dict]
        """
        if headers is None:
            err = "Request headers are missing"
            raise InvalidUsage(
                err,
                log_txt="Error while trying to get user from header. " + err,
                status_code=400,
            )
        token = self.get_token_from_header(headers)
        data = self.decode_token(token)

        user = self.user_model.get_one_object(username=data["sub"])

        if user is None:
            err = "User not found. Please ensure you are using valid credentials"
            raise InvalidCredentials(
                err,
                log_txt="Error while trying to get user from header. User does not exist.",
                status_code=400,
            )

        self._check_token_version(user, data)

        return user, data

    def _check_token_version(self, user, payload):
        """
        Rejects internal tokens whose version claim no longer matches the
        user's current token version: they were revoked by a security event
        (password change, account lock, MFA reset).

        :param user: the user the token belongs to
        :param dict payload: the decoded token payload
        """
        if not self.CHECK_TOKEN_VERSION:
            return
        if not isinstance(payload, dict):
            return
        if payload.get("type") == TOKEN_TYPE_API_KEY:
            # API keys use their own version (akv), checked in authenticate
            return
        if payload.get("iss") != INTERNAL_TOKEN_ISSUER:
            # External (OIDC) tokens are managed by the identity provider
            return
        if int(payload.get("tv", 0)) != int(user.token_version or 0):
            raise InvalidCredentials(
                "The session has been revoked, please log in again",
                status_code=401,
                log_txt=f"Error while user {user.id} tries to authenticate. "
                f"The token version is stale (revoked session).",
            )

    def get_user_from_header(self, headers: Headers = None) -> UserModel:
        """
        Extracts the user from the Authorization headers. Temporary tokens
        carrying a purpose claim are rejected.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the user object
        :rtype: :class:`UserModel`
        """
        user, data = self.get_user_and_payload_from_header(headers)
        if isinstance(data, dict) and data.get("purpose") is not None:
            raise InvalidCredentials(
                "The provided token can only be used for its intended "
                "purpose and has no access to this endpoint",
                log_txt="Error while trying to get user from header. "
                "The token is a temporary purpose token.",
                status_code=403,
            )
        if isinstance(data, dict) and data.get("type") == TOKEN_TYPE_REFRESH:
            raise InvalidCredentials(
                "A refresh token can not be used to access this endpoint",
                log_txt="Error while trying to get user from header. "
                "The token is a refresh token.",
                status_code=401,
            )
        return user

    @staticmethod
    def get_public_keys(provider_url: str) -> dict:
        """
        Gets the public keys from the OIDC provider and caches them

        :param str provider_url: The base URL of the OIDC provider
        :return: Dictionary of kid to public key mappings
        :rtype: dict
        """
        # Fetch keys from provider
        # For Azure AD, we need to use the discovery endpoint to get the jwks_uri
        oid_provider_type = current_app.config["OID_PROVIDER_TYPE"]
        if oid_provider_type == OID_PROVIDER_AZURE:
            # Azure AD uses a different endpoint for JWKS
            # Extract tenant ID from provider URL
            tenant_id = provider_url.split("/")[3]
            jwks_url = (
                f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
            )
        else:
            # AWS Cognito uses the standard well-known endpoint
            # For other providers, use the standard well-known endpoint
            jwks_url = f"{provider_url.rstrip('/')}/.well-known/jwks.json"

        try:
            response = requests.get(jwks_url)
            response.raise_for_status()

            # Convert JWK to RSA public keys using PyJWT's built-in method
            public_keys = {
                key["kid"]: RSAAlgorithm.from_jwk(key)
                for key in response.json()["keys"]
            }

            # Store in cache
            public_keys_cache[provider_url] = public_keys
            return public_keys

        except requests.exceptions.RequestException as e:
            raise CommunicationError(
                "Failed to fetch public keys from authentication provider",
                log_txt=f"Error while fetching public keys from {jwks_url}: {str(e)}",
                status_code=400,
            )

    def verify_token(
        self, token: str, provider_url: str, expected_audience: str
    ) -> dict:
        """
        Verifies an OpenID Connect token

        :param str token: The token to verify
        :param str provider_url: The base URL of the OIDC provider
        :param str expected_audience: The expected audience claim
        :return: The decoded token claims
        :rtype: dict
        """

        # Get unverified header - this will raise jwt.InvalidTokenError if token format is invalid
        unverified_header = jwt.get_unverified_header(token)

        # Check for kid in header
        if "kid" not in unverified_header:

            raise InvalidCredentials(
                "Invalid token: Missing key identifier (kid) in token header",
                log_txt="Error while verifying token. Token header is missing 'kid'.",
                status_code=400,
            )

        kid = unverified_header["kid"]

        # Check if we have the keys in cache and if the kid exists
        public_key = None
        if provider_url in public_keys_cache:
            cached_keys = public_keys_cache[provider_url]
            if kid in cached_keys:
                public_key = cached_keys[kid]

        # If kid not in cache, fetch fresh keys
        if public_key is None:
            public_keys = self.get_public_keys(provider_url)
            if kid not in public_keys:
                raise InvalidCredentials(
                    "Invalid token: Unknown key identifier (kid)",
                    log_txt="Error while verifying token. Key ID not found in public keys.",
                    status_code=400,
                )
            public_key = public_keys[kid]

        # Verify token - this will raise appropriate jwt exceptions that will be caught in decode_token
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=[expected_audience],
            issuer=provider_url,
        )

    @staticmethod
    def _get_permission_for_request(req, user_id):
        method, url = Auth._get_request_info(req)
        user_roles = UserModel.get_one_user(user_id).roles
        if user_roles is None or user_roles == {}:
            raise NoPermission(
                error="You do not have permission to access this endpoint",
                status_code=403,
                log_txt=f"Error while user {user_id} tries to access an endpoint. "
                f"The user does not have any role assigned. ",
            )

        action_id = PERMISSION_METHOD_MAP[method]
        try:
            view_id = ViewModel.query.filter_by(url_rule=url).first().id
        except AttributeError:
            current_app.logger.error(
                "The permission for this endpoint is not in the database."
            )
            raise NoPermission(
                error="The permission for this endpoint is not in the database.",
                status_code=403,
                log_txt=f"Error while user {user_id} tries to access endpoint. "
                f"The permission for this endpoint is not in the database.",
            )

        for role in user_roles:
            has_permission = PermissionViewRoleModel.get_permission(
                role_id=role, api_view_id=view_id, action_id=action_id
            )

            if has_permission:
                return True

        raise NoPermission(
            error="You do not have permission to access this endpoint",
            status_code=403,
            log_txt=f"Error while user {user_id} tries to access endpoint {view_id} with action {action_id}. "
            f"The user does not have permission to access. ",
        )

    @staticmethod
    def _get_request_info(req: Request) -> Tuple[str, str]:
        """
        Function to get the request method and the objective url from the request

        :param req: the request performed to the API REST
        :type req: `Request`
        :return: a tuple containing the request type that is being performed and the objective url
        :rtype: Tuple[str, str]
        """
        return getattr(req, "environ")["REQUEST_METHOD"], getattr(req, "url_rule").rule


class BIAuth(Auth):
    CHECK_TOKEN_VERSION = False

    def __init__(self, user_model=UserModel):
        super().__init__(user_model)

    @staticmethod
    def decode_token(token: str = None) -> dict:
        """
        Decodes a given JSON Web token and extracts the username from the sub claim.

        :param str token: the given JSON Web Token
        :return: dictionary containing the username from the token's sub claim
        :rtype: dict
        """
        try:
            return jwt.decode(
                token, current_app.config["SECRET_BI_KEY"], algorithms="HS256"
            )

        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                "The BI token has expired, please generate a new one",
                log_txt="Error while trying to decode a BI token. The token has expired.",
                status_code=400,
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt="Error while trying to decode token. The token is invalid.",
                status_code=400,
            )

    @staticmethod
    def generate_token(user_id: int = None) -> str:
        """
        Generates a BI token given a user_id. The token contains the username
        in the sub claim and expires after BI_TOKEN_DURATION_DAYS days (it can
        be regenerated with `cornflow users bi_token`).

        :param int user_id: user id to generate the token for
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        user = UserModel.get_one_user(user_id)
        if user is None:
            err = "User does not exist"
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        payload = {
            "exp": datetime.now(timezone.utc)
            + timedelta(days=int(current_app.config["BI_TOKEN_DURATION_DAYS"])),
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
        }

        return jwt.encode(
            payload, current_app.config["SECRET_BI_KEY"], algorithm="HS256"
        )
