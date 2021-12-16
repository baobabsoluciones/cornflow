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
from ..shared.const import AUTH_LDAP, PLANNER_ROLE
from ..shared.exceptions import InvalidUsage, InvalidCredentials, EndpointNotImplemented


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
                "The user has to sing up on the active directory"
            )

        if UserModel.check_username_in_use(kwargs.get("username")):
            raise InvalidCredentials(
                error="Username already in use, please supply another username"
            )

        if UserModel.check_email_in_use(kwargs.get("email")):
            raise InvalidCredentials(
                error="Email already in use, please supply another email address"
            )

        check_pwd = UserModel.check_password_pattern(kwargs.get('password'))
        if not check_pwd["valid"]:
            raise InvalidCredentials(
                error=check_pwd["message"]
            )

        check_email = UserModel.check_email_pattern(kwargs.get("email"))
        if not check_email["valid"]:
            raise InvalidCredentials(
                error=check_email["message"]
            )

        user = UserModel(kwargs)
        user.save()

        user_role = UserRoleModel({"user_id": user.id, "role_id": PLANNER_ROLE})
        user_role.save()

        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.add_all_permissions_to_user(user.id)

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error="Error in generating user token: " + str(e), status_code=400
            )
        log.info("User {} was created".format(user.id))
        return {"token": token, "id": user.id}, 201
