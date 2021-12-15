"""
External endpoint for the user to login to the cornflow webserver
"""

# Import from libraries
from flask import g, current_app, request
from flask_apispec import use_kwargs, marshal_with, doc
from flask_apispec.views import MethodResource
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import UserModel, UserRoleModel
from ..schemas.user import UserSchema, LoginEndpointRequest, CheckTokenEndpointResponse
from ..shared.authentication import Auth
from ..shared.const import AUTH_DB, AUTH_LDAP
from ..shared.exceptions import InvalidUsage, InvalidCredentials, ObjectDoesNotExist
from ..shared.ldap import LDAP
from ..shared.utils import db

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
                error="error in generating user token: " + str(e), status_code=400
            )

        return {"token": token, "id": user.id}, 200

    @doc(description="Check token", tags=["Users"])
    @marshal_with(CheckTokenEndpointResponse)
    def get(self):
        """
        API method to check if a token is valid.

        :param str token: ID of the instance
        :return: A dictionary (containing a boolean 'valid') and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        token = Auth.get_token_from_header(request.headers)
        try:
            Auth.get_user_obj_from_header(request.headers)
        except (InvalidCredentials, ObjectDoesNotExist):
            return {"token": token, "valid": 0}, 200
        return {"token": token, "valid": 1}, 200

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
            log.info("LDAP username {} does not exist and is created".format(username))
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
        except:
            # or we rollback
            db.session.rollback()
        return user
