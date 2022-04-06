"""
External endpoint for the user to signup
"""
# Import from libraries
from flask import current_app
from flask_apispec.views import MethodResource
from flask_apispec import use_kwargs, doc
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import UserModel, PermissionsDAG, UserRoleModel
from ..schemas.user import UserSignupRequest
from ..shared.authentication import Auth
from ..shared.const import AUTH_LDAP, AUTH_OID, PLANNER_ROLE
from cornflow_core.exceptions import (
    InvalidUsage,
    InvalidCredentials,
    EndpointNotImplemented,
)


class SignUpEndpoint(MetaResource, MethodResource):
    """
    Endpoint used to sign up to the cornflow web server.
    """

    @doc(description="Sign up", tags=["Users"])
    @use_kwargs(UserSignupRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to sign up to the cornflow webserver

        :return: A dictionary with a message (either an error during signup or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The user has to sign up on the active directory"
            )
        elif AUTH_TYPE == AUTH_OID:
            raise EndpointNotImplemented(
                "The user has to sign up with the OpenID protocol"
            )

        user = UserModel(kwargs)

        if user.check_username_in_use():
            raise InvalidCredentials(
                error="Username already in use, please supply another username"
            )

        if user.check_email_in_use():
            raise InvalidCredentials(
                error="Email already in use, please supply another email address"
            )

        user.save()

        user_role = UserRoleModel(
            {"user_id": user.id, "role_id": current_app.config["DEFAULT_ROLE"]}
        )
        user_role.save()

        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.add_all_permissions_to_user(user.id)

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error="Error in generating user token: " + str(e), status_code=400
            )
        log.info(f"User {user.id} was created")
        return {"token": token, "id": user.id}, 201
