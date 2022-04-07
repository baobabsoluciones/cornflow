"""

"""
# Global imports
import base64
import jwt
import requests
import requests.exceptions

# Partial imports
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from flask import request, g, current_app
from functools import wraps

# Internal modules imports
from .const import (
    PERMISSION_METHOD_MAP,
    OID_AZURE,
    OID_GOOGLE,
    OID_AZURE_DISCOVERY_COMMON_URL,
    OID_AZURE_DISCOVERY_TENANT_URL,
)

from cornflow_core.exceptions import (
    CommunicationError,
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidData,
    NoPermission,
)

from ..models import ApiViewModel, UserModel, PermissionsDAG, PermissionViewRoleModel

from cornflow_core.authentication import Auth as AuthBase


class Auth(AuthBase):
    user_model = UserModel

    @staticmethod
    def validate_oid_token(token, client_id, tenant_id, issuer, provider):
        """
        :param str token:
        :param str client_id:
        :param str tenant_id:
        :param str issuer:
        :param int provider:
        """
        public_key = Auth._get_public_key(token, tenant_id, provider)
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
                error="The token has expired, please login again", status_code=400
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                error="Invalid token, please try again with a new token",
                status_code=400,
            )

    @staticmethod
    def auth_required(func):
        """
        Auth decorator
        :param func:
        :return:
        """

        @wraps(func)
        def decorated_user(*args, **kwargs):
            user = Auth.get_user_from_header(request.headers)
            Auth._get_permission_for_request(request, user.id)
            g.user = {"id": user.id}
            return func(*args, **kwargs)

        return decorated_user

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
                user_id = Auth.get_user_from_header(request.headers).id
                dag_id = request.json.get("schema", None)
                if dag_id is None:
                    raise InvalidData(
                        error="The request does not specify a schema to use",
                        status_code=400,
                    )
                else:
                    if PermissionsDAG.check_if_has_permissions(user_id, dag_id):
                        # We have permissions
                        return func(*args, **kwargs)
                    else:
                        raise NoPermission(
                            error="You do not have permission to use this DAG",
                            status_code=403,
                        )
            else:
                return func(*args, **kwargs)

        return dag_decorator

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
    def _get_request_info(req):
        return getattr(req, "environ")["REQUEST_METHOD"], getattr(req, "url_rule").rule

    @staticmethod
    def _get_permission_for_request(req, user_id):
        method, url = Auth._get_request_info(req)
        user_roles = UserModel.get_one_user(user_id).roles
        if user_roles is None or user_roles == {}:
            raise NoPermission(
                error="You do not have permission to access this endpoint",
                status_code=403,
            )

        action_id = PERMISSION_METHOD_MAP[method]
        view_id = ApiViewModel.query.filter_by(url_rule=url).first().id

        for role in user_roles:
            has_permission = PermissionViewRoleModel.get_permission(
                role_id=role, api_view_id=view_id, action_id=action_id
            )

            if has_permission:
                return True

        raise NoPermission(
            error="You do not have permission to access this endpoint", status_code=403
        )

    @staticmethod
    def _get_kid(token):
        headers = jwt.get_unverified_header(token)
        if not headers:
            raise InvalidCredentials("Token is missing the headers")
        try:
            return headers["kid"]
        except KeyError:
            raise InvalidCredentials("Token is missing the key identifier")

    @staticmethod
    def _fetch_discovery_meta(tenant_id, provider):
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

    @staticmethod
    def _get_jwks_uri(tenant_id, provider):
        meta = Auth._fetch_discovery_meta(tenant_id, provider)
        if "jwks_uri" in meta:
            return meta["jwks_uri"]
        else:
            raise CommunicationError("jwks_uri not found in the issuer meta")

    @staticmethod
    def _get_jwks(tenant_id, provider):
        jwks_uri = Auth._get_jwks_uri(tenant_id, provider)
        try:
            response = requests.get(jwks_uri)
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            raise CommunicationError(
                f"Error getting issuer jwks from {jwks_uri}", error
            )
        return response.json()

    @staticmethod
    def _get_jwk(kid, tenant_id, provider):
        for jwk in Auth._get_jwks(tenant_id, provider).get("keys"):
            if jwk.get("kid") == kid:
                return jwk
        raise InvalidCredentials("Token has an unknown key identifier")

    @staticmethod
    def _ensure_bytes(key):
        if isinstance(key, str):
            key = key.encode("utf-8")
        return key

    @staticmethod
    def _decode_value(val):
        decoded = base64.urlsafe_b64decode(Auth._ensure_bytes(val) + b"==")
        return int.from_bytes(decoded, "big")

    @staticmethod
    def _rsa_pem_from_jwk(jwk):
        return (
            RSAPublicNumbers(
                n=Auth._decode_value(jwk["n"]), e=Auth._decode_value(jwk["e"])
            )
            .public_key(default_backend())
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    @staticmethod
    def _get_public_key(token, tenant_id, provider):
        kid = Auth._get_kid(token)
        jwk = Auth._get_jwk(kid, tenant_id, provider)
        return Auth._rsa_pem_from_jwk(jwk)
