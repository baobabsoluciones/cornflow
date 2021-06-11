"""
External endpoint for the user to signup
"""
# Import from libraries
from flask_apispec.views import MethodResource
from flask_apispec import use_kwargs, doc
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import UserModel, UserRoleModel
from ..schemas.user import UserSignupRequest
from ..shared.authentication import Auth
from ..shared.const import PLANNER_ROLE
from ..shared.exceptions import (
    InvalidUsage,
    InvalidCredentials,
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

        if UserModel.check_username_in_use(kwargs.get("username")):
            raise InvalidCredentials(
                error="Username already in use, please supply another username"
            )

        if UserModel.check_email_in_use(kwargs.get("email")):
            raise InvalidCredentials(
                error="Email already in use, please supply another email address"
            )

        user = UserModel(kwargs)
        user.save()

        user_role = UserRoleModel({"user_id": user.id, "role_id": PLANNER_ROLE})
        user_role.save()

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error="Error in generating user token: " + str(e), status_code=400
            )
        log.info("User {} was created".format(user.id))
        return {"token": token, "id": user.id}, 201
