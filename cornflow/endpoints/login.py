"""
External endpoint for the user to login to the cornflow webserver
"""
# Import from libraries
from flask import current_app
from flask_apispec import use_kwargs, doc
from flask_apispec.views import MethodResource
from flask_restful import Resource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import UserModel
from ..schemas.user import UserSchema, LoginEndpointRequest
from ..shared.authentication import Auth
from ..shared.const import AUTH_DB, AUTH_LDAP
from ..shared.exceptions import InvalidUsage, InvalidCredentials
from ..shared.ldap import LDAP

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class LoginEndpoint(MetaResource, MethodResource):
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

        if AUTH_TYPE == AUTH_DB:
            user = UserModel.get_one_user_by_email(kwargs.get("email"))

            if not user:
                raise InvalidCredentials()

            if not user.check_hash(kwargs.get("password")):
                raise InvalidCredentials()

        elif AUTH_TYPE == AUTH_LDAP:
            if not LDAP.authenticate(kwargs.get("email"), kwargs.get("password")):
                raise InvalidCredentials()
            user = UserModel.get_one_user_by_username(kwargs.get("email"))

            if not user:
                email = LDAP.get_user_email(kwargs.get("email"))
                if not email:
                    email = ""
                data = {
                    "name": kwargs.get("email"),
                    "password": kwargs.get("password"),
                    "email": email,
                }
                user = UserModel(data=data)
                user.save()
                user = UserModel.get_one_user_by_username(kwargs.get("email"))

        try:
            token = Auth.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                error="error in generating user token: " + str(e), status_code=400
            )

        return {"token": token, "id": user.id}, 200
