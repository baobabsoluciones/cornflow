"""
This file contains the basic auth class that can be used for authentication on the request to the REST API
"""
# Imports from python base libraries
import base64
from datetime import datetime, timedelta
from typing import Union, Tuple

# Import from external libraries
import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from flask import current_app, g, request, Request
from jwt import decode, encode, ExpiredSignatureError, InvalidTokenError
from werkzeug.datastructures import Headers

# Imports from internal modules
from cornflow_core.constants import (
    OID_AZURE,
    OID_AZURE_DISCOVERY_TENANT_URL,
    OID_AZURE_DISCOVERY_COMMON_URL,
    OID_GOOGLE,
)
from cornflow_core.exceptions import (
    InvalidCredentials,
    InvalidUsage,
    ObjectDoesNotExist,
    EndpointNotImplemented,
    CommunicationError,
)
from cornflow_core.models import UserBaseModel


class BaseAuth:
    """
    This class implements the basic auth class, with token generation and decoding, oid token validation
    and an authenticate method.
    """

    def __init__(self, user_model=None):
        if user_model is None:
            self.user_model = UserBaseModel
        self.user_model = user_model

    @staticmethod
    def generate_token(user_id: int = None) -> str:
        """
        Generates a token given a user_id with a duration of one day

        :param int user_id: user code to be encoded in the token to identify the user afterwards
        :return: the generated token
        :rtype: str
        """
        if user_id is None:
            raise InvalidUsage("The user id passed to generate the token is not valid.")

        payload = {
            "exp": datetime.utcnow() + timedelta(days=1),
            "iat": datetime.utcnow(),
            "sub": user_id,
        }

        return encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    @staticmethod
    def decode_token(token: str = None) -> dict:
        """
        Decodes a given JSON Web token and extracts the sub from it to give it back.

        :param str token: the given JSON Web Token
        :return: the sub field of the token as the user_id
        :rtype: dict
        """
        if token is None:
            raise InvalidUsage("The provided token is not valid")
        try:
            payload = decode(
                token, current_app.config["SECRET_KEY"], algorithms="HS256"
            )
            return {"user_id": payload["sub"]}
        except ExpiredSignatureError:
            raise InvalidCredentials("The token has expired, please login again")
        except InvalidTokenError:
            raise InvalidCredentials("Invalid token, please try again with a new token")

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
            raise InvalidCredentials("The token has expired, please login again")
        except jwt.InvalidTokenError:
            raise InvalidCredentials("Invalid token, please try again with a new token")

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
            raise InvalidUsage

        if "Authorization" not in headers:
            raise InvalidCredentials("Auth token is not available")
        auth_header = headers.get("Authorization")
        if not auth_header:
            return ""
        try:
            return auth_header.split(" ")[1]
        except Exception as e:
            raise InvalidCredentials(f"The authorization header has a bad syntax: {e}")

    def get_user_from_header(self, headers: Headers = None) -> UserBaseModel:
        """
        Gets the user represented by the token that has to be in the request headers.

        :param headers: the request headers
        :type headers: `Headers`
        :return: the user object
        :rtype: `UserBaseModel`
        """
        if headers is None:
            raise InvalidUsage(
                "Headers are missing from the request. Authentication was not possible to perform"
            )
        token = self.get_token_from_header(headers)
        data = self.decode_token(token)
        user_id = data["user_id"]
        user = self.user_model.get_one_user(user_id)
        if user is None:
            raise ObjectDoesNotExist("User does not exist, invalid token")
        return user

    def authenticate(self):
        """
        Main method to perform the authentication of the user on the REST API.

        :return: True if the authentication was successful, it raises an exception in case the authentication failed
        or the was an error
        :rtype: bool
        """
        user = self.get_user_from_header(request.headers)
        g.user = user
        return True

    """
    START OF INTERNAL PROTECTED METHODS
    """

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
        headers = jwt.get_unverified_header(token)
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
        except requests.exceptions.HTTPError as error:
            raise CommunicationError(
                f"Error getting issuer discovery meta from {discovery_url}", error
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