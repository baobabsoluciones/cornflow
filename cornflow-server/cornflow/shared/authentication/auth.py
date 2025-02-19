"""
This file contains the auth class that can be used for authentication on the request to the REST API
"""

# Imports from external libraries
import base64
import jwt
import requests

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from datetime import datetime, timedelta
from flask import request, g, current_app, Request
from functools import wraps
from typing import Union, Tuple

from jwt import DecodeError
from werkzeug.datastructures import Headers

# Imports from internal modules
from cornflow.models import (
    PermissionsDAG,
    PermissionViewRoleModel,
    UserModel,
    ViewModel,
)
from cornflow.shared.const import (
    OID_AZURE,
    OID_AZURE_DISCOVERY_TENANT_URL,
    OID_AZURE_DISCOVERY_COMMON_URL,
    OID_GOOGLE,
    OID_COGNITO,
    PERMISSION_METHOD_MAP,
    AUTH_EXTERNAL,
)
from cornflow.shared.exceptions import (
    CommunicationError,
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidData,
    InvalidUsage,
    NoPermission,
    ObjectDoesNotExist,
)


class Auth:
    def __init__(self, user_model=UserModel):
        self.user_model = user_model
        self._cognito_jwks = None
        self._cognito_jwks_last_update = None

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
        Generates a token given a user_id with a duration of one day

        :param int user_id: user code to be encoded in the token to identify the user afterwards
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        payload = {
            "exp": datetime.utcnow()
            + timedelta(hours=float(current_app.config["TOKEN_DURATION"])),
            "iat": datetime.utcnow(),
            "sub": user_id,
        }

        return jwt.encode(
            payload, current_app.config["SECRET_TOKEN_KEY"], algorithm="HS256"
        )

    @staticmethod
    def decode_token(token: str = None) -> dict:
        """
        Decodes a given JSON Web token and extracts the sub from it to give it back.

        :param str token: the given JSON Web Token
        :return: the sub field of the token as the user_id or username depending on auth type
        :rtype: dict
        """
        if token is None:
            err = "The provided token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to decode token. " + err
            )
        try:
            # If we're using external auth, first try to decode as internal token for service users
            if current_app.config["AUTH_TYPE"] == AUTH_EXTERNAL:
                try:
                    # Try to decode as internal token
                    payload = jwt.decode(
                        token, current_app.config["SECRET_TOKEN_KEY"], algorithms="HS256"
                    )
                    # Check if it's a service user with password login enabled
                    user = UserModel.get_one_user(payload["sub"])
                    if user and user.is_service_user() and current_app.config["SERVICE_USER_ALLOW_PASSWORD_LOGIN"] == 1:
                        return {"user_id": payload["sub"]}
                except jwt.InvalidTokenError:
                    pass  # Not an internal token, continue with Cognito validation
                
                # For non-service users or invalid internal tokens, validate with Cognito
                decoded = Auth().validate_external_cognito_token(token)
                return {"username": decoded["sub"]}
            
            # Otherwise use our internal token
            payload = jwt.decode(
                token, current_app.config["SECRET_TOKEN_KEY"], algorithms="HS256"
            )
            return {"user_id": payload["sub"]}
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                "The token has expired, please login again",
                log_txt="Error while trying to decode token. The token has expired.",
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt="Error while trying to decode token. The token is invalid.",
            )

    def validate_oid_token(
        self, token: str, client_id: str, tenant_id: str, issuer: str, provider: int
    ) -> dict:
        """
        This method takes a token issued by an OID provider, the relevant information about the OID provider
        and validates that the token was generated by such source, is valid and extracts the information
        in the token for its use during the login process

        :param str token: the received token
        :param str client_id: the identifier from the client
        :param str tenant_id: the identifier for the tenant
        :param str issuer: the identifier for the issuer of the token
        :param int provider: the identifier for the provider of the token
        :return: the decoded token as a dictionary
        :rtype: dict
        """
        public_key = self._get_public_key(token, tenant_id, provider)
        try:
            decoded = jwt.decode(
                token,
                public_key,
                verify=True,
                algorithms=["RS256"],
                audience=[client_id],
                issuer=issuer,
            )
            return decoded
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                "The token has expired, please login again",
                log_txt="Error while trying to validate a token. The token has expired.",
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt="Error while trying to validate a token. The token is not valid.",
            )

    @staticmethod
    def get_token_from_header(headers: Headers = None) -> str:
        """
        Extracts the token given on the request from the Authorization headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the extracted token
        :rtype: str
        """
        if headers is None:
            raise InvalidUsage(
                log_txt="Error while trying to get a token from header. The header is invalid."
            )

        if "Authorization" not in headers:
            raise InvalidCredentials(
                "Auth token is not available",
                log_txt="Error while trying to get a token from header. The auth token is not available.",
            )
        auth_header = headers.get("Authorization")
        if not auth_header:
            return ""
        try:
            return auth_header.split(" ")[1]
        except Exception as e:
            err = f"The authorization header has a bad syntax: {e}"
            raise InvalidCredentials(
                err, log_txt=f"Error while trying to get a token from header. " + err
            )

    def get_user_from_header(self, headers: Headers = None) -> UserModel:
        """
        Gets the user represented by the token that has to be in the request headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the user object
        :rtype: `UserBaseModel`
        """
        if headers is None:
            err = "Headers are missing from the request. Authentication was not possible to perform."
            raise InvalidUsage(
                err, log_txt="Error while trying to get user from header. " + err
            )
        token = self.get_token_from_header(headers)
        data = self.decode_token(token)
        
        # For external auth, we get the username
        if "username" in data:
            user = self.user_model.get_one_object(username=data["username"])
        # For internal auth, we get the user_id
        else:
            user = self.user_model.get_one_user(data["user_id"])
            
        if user is None:
            err = "User does not exist, invalid token."
            raise ObjectDoesNotExist(
                err, log_txt="Error while trying to get user from header. " + err
            )
        return user

    @staticmethod
    def return_user_from_token(token):
        """
        Function used for internal testing. Given a token gives back the user_id encoded in it.

        :param str token: the given token
        :return: the user id code.
        :rtype: int
        """
        user_id = Auth.decode_token(token)["user_id"]
        return user_id

    """
    START OF INTERNAL PROTECTED METHODS
    """

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

    @staticmethod
    def _get_key_id(token: str) -> str:
        """
        Function to get the Key ID from the token

        :param str token: the given token
        :return: the key identifier
        :rtype: str
        """
        try:
            headers = jwt.get_unverified_header(token)
        except DecodeError as err:
            raise InvalidCredentials("Token is not valid")
        if not headers:
            raise InvalidCredentials("Token is missing the headers")
        try:
            return headers["kid"]
        except KeyError:
            raise InvalidCredentials("Token is missing the key identifier")

    @staticmethod
    def _fetch_discovery_meta(tenant_id: str, provider: int) -> dict:
        """
        Function to return a dictionary with the discovery URL of the provider

        :param str tenant_id: the tenant id
        :param int provider: the provider information
        :return: the different urls to be discovered on the provider
        :rtype: dict
        """
        if provider == OID_AZURE:
            oid_tenant_url = OID_AZURE_DISCOVERY_TENANT_URL
            oid_common_url = OID_AZURE_DISCOVERY_COMMON_URL
        elif provider == OID_GOOGLE:
            raise EndpointNotImplemented("The OID provider configuration is not valid")
        else:
            raise EndpointNotImplemented("The OID provider configuration is not valid")

        discovery_url = (
            oid_tenant_url.format(tenant_id=tenant_id) if tenant_id else oid_common_url
        )
        try:
            response = requests.get(discovery_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise CommunicationError(
                f"Error getting issuer discovery meta from {discovery_url}"
            )
        return response.json()

    def _get_json_web_keys_uri(self, tenant_id: str, provider: int) -> str:
        """
        Returns the JSON Web Keys URI

        :param str tenant_id: the tenant id
        :param int provider: the provider information
        :return: the URI from where to get the JSON Web Keys
        :rtype: str
        """
        meta = self._fetch_discovery_meta(tenant_id, provider)
        if "jwks_uri" in meta:
            return meta["jwks_uri"]
        else:
            raise CommunicationError("jwks_uri not found in the issuer meta")

    def _get_json_web_keys(self, tenant_id: str, provider: int) -> dict:
        """
        Function to get the json web keys from the tenant id and the provider

        :param str tenant_id: the tenant id
        :param int provider: the provider information
        :return: the JSON Web Keys dict
        :rtype: dict
        """
        json_web_keys_uri = self._get_json_web_keys_uri(tenant_id, provider)
        try:
            response = requests.get(json_web_keys_uri)
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise CommunicationError(
                f"Error getting issuer jwks from {json_web_keys_uri}", error
            )
        return response.json()

    def _get_jwk(self, kid: str, tenant_id: str, provider: int) -> dict:
        """
        Function to get the JSON Web Key from the key identifier, the tenant id and the provider information

        :param str kid: the key identifier
        :param str tenant_id: the tenant information
        :param int provider: the provider information
        :return: the JSON Web Key
        :rtype: dict
        """
        for jwk in self._get_json_web_keys(tenant_id, provider).get("keys"):
            if jwk.get("kid") == kid:
                return jwk
        raise InvalidCredentials("Token has an unknown key identifier")

    @staticmethod
    def _ensure_bytes(key: Union[str, bytes]) -> bytes:
        """
        Function that ensures that the key is in bytes format

        :param str | bytes key:
        :return: the key on bytes format
        :rtype: bytes
        """
        if isinstance(key, str):
            key = key.encode("utf-8")
        return key

    def _decode_value(self, val: Union[str, bytes]) -> int:
        """
        Function that ensures that the value is decoded as a big int

        :param str | bytes val: the value that has to be decoded
        :return: the decoded value as a big int
        :rtype: int
        """
        decoded = base64.urlsafe_b64decode(self._ensure_bytes(val) + b"==")
        return int.from_bytes(decoded, "big")

    def _rsa_pem_from_jwk(self, jwk: dict) -> bytes:
        """
        Returns the private key from the JSON Web Key encoded as PEM

        :param dict jwk: the JSON Web Key
        :return: the RSA PEM key serialized as bytes
        :rtype: bytes
        """
        return (
            RSAPublicNumbers(
                n=self._decode_value(jwk["n"]),
                e=self._decode_value(jwk["e"]),
            )
            .public_key(default_backend())
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    def _get_public_key(self, token: str, tenant_id: str, provider: int):
        """
        This method returns the public key from the given token, ensuring that
        the tenant information and provider are correct

        :param str token: the given token
        :param str tenant_id: the tenant information
        :param int provider: the token provider information
        :return: the public key in the token or it raises an error
        :rtype: str
        """
        kid = self._get_key_id(token)
        jwk = self._get_jwk(kid, tenant_id, provider)
        return self._rsa_pem_from_jwk(jwk)

    def validate_external_cognito_token(self, token: str) -> dict:
        """
        Validates a JWT token when the application is in external auth mode using AWS Cognito.
        
        :param str token: The JWT token from Cognito
        :return: The decoded token payload
        :rtype: dict
        """
        try:
            headers = jwt.get_unverified_header(token)
            kid = headers['kid']
            
            # Get the public key for this specific key ID
            public_key = self._get_cognito_public_key(kid)
            
            # Decode and verify the token
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=current_app.config['COGNITO_APP_CLIENT_ID'],
                issuer=f"https://cognito-idp.{current_app.config['COGNITO_REGION']}.amazonaws.com/{current_app.config['COGNITO_USER_POOL_ID']}"
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                "The token has expired, please login again",
                log_txt="Error while trying to validate Cognito token. The token has expired."
            )
        except jwt.InvalidTokenError as e:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt=f"Error while trying to validate Cognito token. The token is invalid: {str(e)}"
            )

    def _get_cognito_public_key(self, kid: str) -> str:
        """
        Gets the public key from Cognito's JWKS endpoint for a specific key ID.
        Implements caching to avoid requesting the keys on every validation.
        
        :param str kid: The key ID from the token header
        :return: The public key in PEM format
        :rtype: str
        """
        # Check if we need to refresh the JWKS
        now = datetime.utcnow()
        if (self._cognito_jwks is None or 
            self._cognito_jwks_last_update is None or
            now - self._cognito_jwks_last_update > timedelta(hours=24)):
            
            jwks_url = f"https://cognito-idp.{current_app.config['COGNITO_REGION']}.amazonaws.com/{current_app.config['COGNITO_USER_POOL_ID']}/.well-known/jwks.json"
            response = requests.get(jwks_url)
            response.raise_for_status()
            self._cognito_jwks = response.json()['keys']
            self._cognito_jwks_last_update = now

        # Find the key matching the kid
        key = next((k for k in self._cognito_jwks if k['kid'] == kid), None)
        if not key:
            raise InvalidCredentials(
                "Invalid token key ID",
                log_txt=f"Error while trying to validate Cognito token. Key ID {kid} not found in JWKS."
            )

        return self._rsa_pem_from_jwk(key)


class BIAuth(Auth):
    def __init__(self, user_model=UserModel):
        super().__init__(user_model)

    @staticmethod
    def decode_token(token: str = None) -> dict:
        """
        Decodes a given JSON Web token and extracts the sub from it to give it back.

        :param str token: the given JSON Web Token
        :return: the sub field of the token as the user_id
        :rtype: dict
        """
        if token is None:
            err = "The provided token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to decode token. " + err
            )
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_BI_KEY"], algorithms="HS256"
            )
            return {"user_id": payload["sub"]}
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                "Invalid token, please try again with a new token",
                log_txt="Error while trying to decode token. The token is invalid.",
            )

    @staticmethod
    def generate_token(user_id: int = None) -> str:
        """
        Generates a token given a user_id with a duration of one day

        :param int user_id: user code to be encoded in the token to identify the user afterward.
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            err = "The user id passed to generate the token is not valid."
            raise InvalidUsage(
                err, log_txt="Error while trying to generate token. " + err
            )

        payload = {
            "iat": datetime.utcnow(),
            "sub": user_id,
        }

        return jwt.encode(
            payload, current_app.config["SECRET_BI_KEY"], algorithm="HS256"
        )
