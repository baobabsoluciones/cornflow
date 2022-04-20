"""

"""

from flask import current_app

from cornflow_core.authentication import BaseAuth
from cornflow_core.constants import AUTH_LDAP, AUTH_OID
from cornflow_core.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
)
from .meta_resource import BaseMetaResource


class SignupBaseEndpoint(BaseMetaResource):
    def __init__(self):
        super().__init__()
        self.auth_class = BaseAuth
        self.user_role_association = None

    def sign_up(self, **kwargs):
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The user has to sign up on the active directory"
            )
        elif AUTH_TYPE == AUTH_OID:
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
