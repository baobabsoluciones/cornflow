"""
This file contains the base for a sign up endpoint
"""

from flask import current_app

from cornflow_core.authentication import BaseAuth
from cornflow_core.constants import AUTH_LDAP, AUTH_OID
from cornflow_core.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
)
from cornflow_core.models import UserBaseModel, UserRoleBaseModel
from .meta_resource import BaseMetaResource


class SignupBaseEndpoint(BaseMetaResource):
    """
    Ths base for the sign up endpoint
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserBaseModel
        self.auth_class = BaseAuth
        self.user_role_association = UserRoleBaseModel

    def sign_up(self, **kwargs):
        """
        The method in charge of performing the sign up of users

        :param kwargs: the keyword arguments needed to perform the sign up
        :return: a dictionary with the newly issued token and the user id, and a status code
        """
        auth_type = current_app.config["AUTH_TYPE"]
        if auth_type == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The user has to sign up on the active directory"
            )
        elif auth_type == AUTH_OID:
            raise EndpointNotImplemented(
                "The user has to sign up with the OpenID protocol"
            )

        user = self.data_model(kwargs)

        if user.check_username_in_use():
            raise InvalidCredentials(
                error="Username already in use, please supply another username"
            )

        if user.check_email_in_use():
            raise InvalidCredentials(
                error="Email already in use, please supply another email address"
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
                error="Error in generating user token: " + str(e), status_code=400
            )

        return {"token": token, "id": user.id}, 201
