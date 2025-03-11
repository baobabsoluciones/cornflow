"""
External endpoint for the user to log in to the cornflow webserver
"""

from datetime import datetime, timezone, timedelta

# Partial imports
from flask import current_app, request
from flask_apispec import use_kwargs, doc
from sqlalchemy.exc import IntegrityError, DBAPIError

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import UserModel, UserRoleModel, PermissionsDAG
from cornflow.schemas.user import LoginEndpointRequest, LoginOpenAuthRequest
from cornflow.shared import db
from cornflow.shared.authentication import Auth, LDAPBase
from cornflow.shared.const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OID,
)
from cornflow.shared.exceptions import (
    ConfigurationError,
    InvalidCredentials,
    InvalidUsage,
)


class LoginBaseEndpoint(BaseMetaResource):
    """
    Base endpoint to perform a login action from a user
    """

    def __init__(self):
        super().__init__()
        self.ldap_class = LDAPBase
        self.user_role_association = UserRoleModel

    def log_in(self, **kwargs):
        """
        This method is in charge of performing the log in of the user

        :param kwargs: keyword arguments passed for the login, these can be username, password or a token
        :return: the response of the login, or it raises an error. The correct response is a dict
        with the newly issued token and the user id, and a status code of 200
        :rtype: dict
        """
        auth_type = current_app.config["AUTH_TYPE"]
        response = {}

        if auth_type == AUTH_DB:
            user = self.auth_db_authenticate(**kwargs)
            response.update({"change_password": check_last_password_change(user)})
            current_app.logger.info(
                f"User {user.id} logged in successfully using database authentication"
            )
        elif auth_type == AUTH_LDAP:
            user = self.auth_ldap_authenticate(**kwargs)
            current_app.logger.info(
                f"User {user.id} logged in successfully using LDAP authentication"
            )
        elif auth_type == AUTH_OID:
            if kwargs.get("username") and kwargs.get("password"):
                if not current_app.config.get("SERVICE_USER_ALLOW_PASSWORD_LOGIN", 0):
                    raise InvalidUsage(
                        "Must provide a token in Authorization header. Cannot log in with username and password",
                        400,
                    )
                user = self.auth_oid_authenticate(
                    username=kwargs["username"], password=kwargs["password"]
                )
                current_app.logger.info(
                    f"Service user {user.id} logged in successfully using password"
                )
                token = self.auth_class.generate_token(user.id)
            else:
                token = self.auth_class().get_token_from_header(request.headers)
                user = self.auth_oid_authenticate(token=token)
                current_app.logger.info(
                    f"User {user.id} logged in successfully using OpenID authentication"
                )

            response.update({"token": token, "id": user.id})
            return response, 200
        else:
            raise ConfigurationError()

        try:
            token = self.auth_class.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(f"Error in generating user token: {str(e)}", 400)

        response.update({"token": token, "id": user.id})

        return response, 200

    def auth_db_authenticate(self, username, password):
        """
        Method in charge of performing the authentication against the database

        :param str username: the username of the user to log in
        :param str password:  the password of the user to log in
        :return: the user object, or it raises an error if it has not been possible to log in
        :rtype: :class:`UserModel`
        """
        user = self.data_model.get_one_object(username=username)

        if not user:
            raise InvalidCredentials()

        if not user.check_hash(password):
            raise InvalidCredentials()

        return user

    def auth_ldap_authenticate(self, username, password):
        """
        Method in charge of performing the authentication against the ldap server

        :param str username: the username of the user to log in
        :param str password:  the password of the user to log in
        :return: the user object, or it raises an error if it has not been possible to log in
        :rtype: :class:`UserModel`
        """
        ldap_obj = self.ldap_class(current_app.config)
        if not ldap_obj.authenticate(username, password):
            raise InvalidCredentials()
        user = self.data_model.get_one_object(username=username)
        if not user:
            current_app.logger.info(
                f"LDAP user {username} does not exist and is created"
            )
            email = ldap_obj.get_user_email(username)
            if not email:
                email = ""
            data = {"username": username, "email": email}
            user = self.data_model(data=data)
            user.save()

        roles = ldap_obj.get_user_roles(username)

        try:
            self.user_role_association.del_one_user(user.id)
            for role in roles:
                user_role = self.user_role_association(
                    data={"user_id": user.id, "role_id": role}
                )
                user_role.save()

        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Integrity error on user role assignment on log in: {e}"
            )
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unknown error on user role assignment on log in: {e}"
            )

        return user

    def auth_oid_authenticate(
        self, token: str = None, username: str = None, password: str = None
    ):
        """
        Method in charge of performing the authentication using OpenID Connect tokens.
        Supports any OIDC provider configured via provider_url.

        :param str token: the JWT token from the OIDC provider
        :param str username: username for service users
        :param str password: password for service users
        :return: the user object, or it raises an error if it has not been possible to log in
        :rtype: :class:`UserModel`
        """
        if token:

            decoded_token = self.auth_class().decode_token(token)

            username = decoded_token.get("sub")

            user = self.data_model.get_one_object(username=username)

            if not user:
                current_app.logger.info(
                    f"OpenID user {username} does not exist and is created"
                )

                email = decoded_token.get("email", f"{username}@cornflow.org")
                first_name = decoded_token.get("given_name", "")
                last_name = decoded_token.get("family_name", "")

                data = {
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                }

                user = self.data_model(data=data)
                user.save()

                user_role = self.user_role_association(
                    {
                        "user_id": user.id,
                        "role_id": int(current_app.config["DEFAULT_ROLE"]),
                    }
                )
                user_role.save()
                if int(current_app.config["OPEN_DEPLOYMENT"]) == 1:
                    PermissionsDAG.add_all_permissions_to_user(user.id)

            return user

        elif username and password:
            user = self.auth_db_authenticate(username, password)
            if user.is_service_user():
                return user
            raise InvalidUsage("Invalid request")
        else:
            raise InvalidUsage("Invalid request")


def check_last_password_change(user):
    """
    Check if the user needs to change their password based on the password rotation time.

    :param user: The user object to check
    :return: True if password needs to be changed, False otherwise
    :rtype: bool
    """
    if user.pwd_last_change:
        # Handle the case where pwd_last_change is already a datetime object
        if isinstance(user.pwd_last_change, datetime):
            # If it's a naive datetime (no timezone info), make it timezone-aware
            if user.pwd_last_change.tzinfo is None:
                last_change = user.pwd_last_change.replace(tzinfo=timezone.utc)
            else:
                # Already timezone-aware
                last_change = user.pwd_last_change
        else:
            # It's a timestamp (integer), convert to datetime
            last_change = datetime.fromtimestamp(user.pwd_last_change, timezone.utc)

        # Get current time with UTC timezone for proper comparison
        current_time = datetime.now(timezone.utc)

        # Calculate the expiration time based on the password rotation setting
        expiration_time = last_change + timedelta(
            days=int(current_app.config["PWD_ROTATION_TIME"])
        )

        # Compare the timezone-aware datetimes
        if expiration_time < current_time:
            return True
    return False


class LoginEndpoint(LoginBaseEndpoint):
    """
    Endpoint used to do the login to the cornflow webserver
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginEndpointRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to log in in to the web server.

        :return: A dictionary with a message (either an error during login or the generated token for the user session)
          and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """

        return self.log_in(**kwargs)


class LoginOpenAuthEndpoint(LoginBaseEndpoint):
    """ """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    @doc(description="Log in", tags=["Users"])
    @use_kwargs(LoginOpenAuthRequest, location="json")
    def post(self, **kwargs):
        """ """
        return self.log_in(**kwargs)
