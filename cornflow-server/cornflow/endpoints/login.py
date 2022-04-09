"""
External endpoint for the user to login to the cornflow webserver
"""

# Full import from libraries
import logging as log

# Partial imports
from flask import g, current_app
from flask_apispec import use_kwargs, doc
from flask_apispec.views import MethodResource
from sqlalchemy.exc import DBAPIError, IntegrityError

# Import from internal modules
from .meta_resource import MetaResource
from ..models import PermissionsDAG, UserModel, UserRoleModel
from ..schemas.user import LoginEndpointRequest, LoginOpenAuthRequest
from ..shared.authentication import Auth
from ..shared.const import (
    AUTH_DB,
    AUTH_LDAP,
    OID_AZURE,
    OID_GOOGLE,
    OID_NONE,
    PLANNER_ROLE,
)
from cornflow_core.exceptions import (
    InvalidUsage,
    InvalidCredentials,
    EndpointNotImplemented,
)
from ..shared.ldap import LDAP
from cornflow_core.shared import database as db
from cornflow_core.resources import BaseMetaResource


class LoginEndpoint(BaseMetaResource, MethodResource):
    """
    Endpoint used to do the login to the cornflow webserver
    """

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginEndpointRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to log in in to the web server.

        :return: A dictionary with a message (either an error during login or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        username, password = kwargs.get("username"), kwargs.get("password")

        if AUTH_TYPE == AUTH_DB:
            user = self.auth_db_authenticate(username, password)
        elif AUTH_TYPE == AUTH_LDAP:
            user = self.auth_ldap_authenticate(username, password)
        else:
            raise InvalidUsage("No authentication method configured in server")

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error=f"error in generating user token: {str(e)}", status_code=400
            )

        return {"token": token, "id": user.id}, 200

    @staticmethod
    def auth_db_authenticate(username, password):
        user = UserModel.get_one_user_by_username(username)

        if not user:
            raise InvalidCredentials()

        if not user.check_hash(password):
            raise InvalidCredentials()

        return user

    @staticmethod
    def auth_ldap_authenticate(username, password):
        ldap_obj = LDAP(current_app.config, g)
        if not ldap_obj.authenticate(username, password):
            raise InvalidCredentials()
        user = UserModel.get_one_user_by_username(username)

        if not user:
            log.info(f"LDAP username {username} does not exist and is created")
            email = ldap_obj.get_user_email(username)
            if not email:
                email = ""
            data = {"username": username, "email": email}
            user = UserModel(data=data)
            user.save()
        # regardless whether the user is new or not:
        # we update the roles it has according to ldap
        roles = ldap_obj.get_user_roles(username)

        try:
            # we first remove all roles for the user
            UserRoleModel.del_one_user(user.id)
            # then we create an assignment for each role it has access to
            for role in roles:
                user_role = UserRoleModel({"user_id": user.id, "role_id": role})
                db.session.add(user_role)
            # we only commit if everything went well
            db.session.commit()
        except IntegrityError as e:
            # or we rollback
            db.session.rollback()
            log.error(f"Integrity error on user role assignment on log in: {e}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on user role assignment on log in: {e}")

        return user


class LoginOpenAuthEndpoint(BaseMetaResource, MethodResource):
    """ """

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginOpenAuthRequest, location="json")
    def post(self, **kwargs):
        """ """
        info = self.check_token(kwargs.get("token"))
        user = UserModel.get_one_user_by_username(info["preferred_username"])

        # If the user does not exist we create it and assign it the default role and dag permissions
        if not user:
            log.info(
                f"OpenID username {info['preferred_username']} does not exist and is created"
            )
            data = {
                "username": info["preferred_username"],
                "email": info["preferred_username"],
            }
            user = UserModel(data=data)
            user.save()

            UserRoleModel.del_one_user(user.id)
            user_role = UserRoleModel(
                {"user_id": user.id, "role_id": current_app.config["DEFAULT_ROLE"]}
            )
            user_role.save()

            if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
                PermissionsDAG.delete_all_permissions_from_user(user.id)
                PermissionsDAG.add_all_permissions_to_user(user.id)

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error=f"error in generating user token: {str(e)}", status_code=400
            )

        return {"token": token, "id": user.id}, 200

    @staticmethod
    def check_token(token):
        OID_PROVIDER = int(current_app.config["OID_PROVIDER"])

        client_id = current_app.config["OID_CLIENT_ID"]
        tenant_id = current_app.config["OID_TENANT_ID"]
        issuer = current_app.config["OID_ISSUER"]

        if client_id is None or tenant_id is None or issuer is None:
            raise EndpointNotImplemented("The OID provider configuration is not valid")

        if OID_PROVIDER == OID_AZURE:
            decoded_token = Auth().validate_oid_token(
                token, client_id, tenant_id, issuer, OID_PROVIDER
            )

        elif OID_PROVIDER == OID_GOOGLE:
            raise EndpointNotImplemented("The selected OID provider is not implemented")
        elif OID_PROVIDER == OID_NONE:
            raise EndpointNotImplemented("The OID provider configuration is not valid")
        else:
            raise EndpointNotImplemented("The OID provider configuration is not valid")

        return decoded_token
