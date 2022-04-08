import base64
from datetime import datetime, timedelta
from typing import Dict

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from flask import current_app, g, request
from jwt import decode, encode, ExpiredSignatureError, InvalidTokenError
from werkzeug.datastructures import Headers

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
    """ """

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
    def decode_token(token: str = None) -> Dict:
        """

        :param str token:
        :return:
        :rtype:
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

    @staticmethod
    def get_token_from_header(headers: Headers = None) -> str:
        """

        :param headers:
        :type headers: `Headers`
        :return:
        :rtype:
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

        :param headers:
        :type headers: `Headers`
        :return:
        :rtype:
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
        user = self.get_user_from_header(request.headers)
        g.user = user
        return True

    """
    START OF INTERNAL PROTECTED METHODS
    """

    @staticmethod
    def _get_request_info(req):
        return getattr(req, "environ")["REQUEST_METHOD"], getattr(req, "url_rule").rule

    def _get_kid(self, token):
        headers = jwt.get_unverified_header(token)
        if not headers:
            raise InvalidCredentials("Token is missing the headers")
        try:
            return headers["kid"]
        except KeyError:
            raise InvalidCredentials("Token is missing the key identifier")

    def _fetch_discovery_meta(self, tenant_id, provider):
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

    def _get_jwks_uri(self, tenant_id, provider):
        meta = self._fetch_discovery_meta(tenant_id, provider)
        if "jwks_uri" in meta:
            return meta["jwks_uri"]
        else:
            raise CommunicationError("jwks_uri not found in the issuer meta")

    def _get_jwks(self, tenant_id, provider):
        jwks_uri = self._get_jwks_uri(tenant_id, provider)
        try:
            response = requests.get(jwks_uri)
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise CommunicationError(
                f"Error getting issuer jwks from {jwks_uri}", error
            )
        return response.json()

    def _get_jwk(self, kid, tenant_id, provider):
        for jwk in self._get_jwks(tenant_id, provider).get("keys"):
            if jwk.get("kid") == kid:
                return jwk
        raise InvalidCredentials("Token has an unknown key identifier")

    def _ensure_bytes(self, key):
        if isinstance(key, str):
            key = key.encode("utf-8")
        return key

    def _decode_value(self, val):
        decoded = base64.urlsafe_b64decode(self._ensure_bytes(val) + b"==")
        return int.from_bytes(decoded, "big")

    def _rsa_pem_from_jwk(self, jwk):
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

    def _get_public_key(self, token, tenant_id, provider):
        kid = self._get_kid(token)
        jwk = self._get_jwk(kid, tenant_id, provider)
        return self._rsa_pem_from_jwk(jwk)
