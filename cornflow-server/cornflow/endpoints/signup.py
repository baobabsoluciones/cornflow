"""
External endpoint for the user to signup
"""

# Import from libraries
from flask import current_app
from flask_apispec import use_kwargs, doc

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import PermissionsDAG, UserRoleModel, UserModel
from cornflow.schemas.user import SignupRequest
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import AUTH_LDAP, AUTH_OID, ADMIN_ROLE, SIGNUP_WITH_NO_AUTH
from cornflow.shared.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
)


class SignUpEndpoint(BaseMetaResource):
    """
    Endpoint used to sign up to the cornflow web server.
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Sign up", tags=["Users"])
    @authenticate(
        auth_class=Auth(),
        optional_auth="SIGNUP_ACTIVATED",
        no_auth_list=[SIGNUP_WITH_NO_AUTH],
    )
    @use_kwargs(SignupRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to sign up to the cornflow webserver

        :return: A dictionary with a message (either an error during signup or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        content, status = self.sign_up(**kwargs)

        if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
            PermissionsDAG.add_all_permissions_to_user(content["id"])

        return content, status

    def sign_up(self, **kwargs):
        """
        The method in charge of performing the sign up of users

        :param kwargs: the keyword arguments needed to perform the sign up
        :return: a dictionary with the newly issued token and the user id, and a status code
        """
        auth_type = current_app.config["AUTH_TYPE"]
        if auth_type == AUTH_LDAP:
            err = "The user has to sign up on the active directory"
            raise EndpointNotImplemented(
                err, log_txt="Error while user tries to sign up. " + err
            )
        elif auth_type == AUTH_OID:
            err = "The user has to sign up with the OpenID protocol"
            raise EndpointNotImplemented(
                err, log_txt="Error while user tries to sign up. " + err
            )

        user = self.data_model(kwargs)

        if user.check_username_in_use():
            raise InvalidCredentials(
                error="Username already in use, please supply another username",
                log_txt="Error while user tries to sign up. Username already in use.",
            )

        if user.check_email_in_use():
            raise InvalidCredentials(
                error="Email already in use, please supply another email address",
                log_txt="Error while user tries to sign up. Email already in use.",
            )

        user.save()

        user_role = self.user_role_association(
            {"user_id": user.id, "role_id": current_app.config["DEFAULT_ROLE"]}
        )

        user_role.save()

        try:
            token = self.auth_class.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error="Error in generating user token: " + str(e),
                status_code=400,
                log_txt="Error while user tries to sign up. Unable to generate token.",
            )
        current_app.logger.info(f"New user created: {user}")
        return {"token": token, "id": user.id}, 201
