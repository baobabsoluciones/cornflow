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
    UserModel,
    ViewModel,
)
from cornflow.shared.const import (
    AUTH_OID,
    PERMISSION_METHOD_MAP,
    INTERNAL_TOKEN_ISSUER,
)
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
    def __init__(self, user_model=UserModel):
        self.user_model = user_model

    def authenticate(self):
        user = self.get_user_from_header(request.headers)
        Auth._get_permission_for_request(request, user.id)
        g.user = user
        return True

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
    def generate_token(user_id: int = None) -> str:
        """
        Generates a token given a user_id. The token will contain the username in the sub claim.

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
            + timedelta(hours=float(current_app.config["TOKEN_DURATION"])),
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
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

    def get_user_from_header(self, headers: Headers = None) -> UserModel:
        """
        Extracts the user from the Authorization headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the user object
        :rtype: :class:`UserModel`
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
                error="You do not have permission to access this endpoint",
                status_code=403,
                log_txt=f"Error while user {user_id} tries to access endpoint. "
                f"The user does not permission to access. ",
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
            f"The user does not permission to access. ",
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

        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt="Error while trying to decode token. The token is invalid.",
                status_code=400,
            )

    @staticmethod
    def generate_token(user_id: int = None) -> str:
        """
        Generates a token given a user_id. The token will contain the username in the sub claim.
        BI tokens do not include expiration time.

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
            "iat": datetime.now(timezone.utc),
            "sub": user.username,
            "iss": INTERNAL_TOKEN_ISSUER,
        }

        return jwt.encode(
            payload, current_app.config["SECRET_BI_KEY"], algorithm="HS256"
        )
