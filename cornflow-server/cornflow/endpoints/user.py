"""
Endpoints for the user profiles
"""
# Full imports
import logging as log

from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
    NoPermission,
    ObjectDoesNotExist,
)

# Partial imports from libraries
from cornflow_core.resources import BaseMetaResource
from cornflow_core.resources.recover_password import RecoverPasswordBaseEndpoint
from cornflow_core.shared import check_email_pattern, check_password_pattern
from cornflow_core.shared import db
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc
from sqlalchemy.exc import DBAPIError, IntegrityError

# Import from internal modules
from ..models import UserModel, UserRoleModel
from ..schemas.user import (
    RecoverPasswordRequest,
    UserDetailsEndpointResponse,
    UserEditRequest,
    UserEndpointResponse,
    UserSchema,
)
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, AUTH_LDAP, ALL_DEFAULT_ROLES

# Initialize the schema that the endpoint uses
user_schema = UserSchema()


class UserEndpoint(BaseMetaResource):
    """
    Endpoint with a get method which gives back all the info related to the users.
    Including their instances and executions
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel

    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    @doc(description="Get all users", tags=["Users"])
    @authenticate(auth_class=Auth())
    @marshal_with(UserEndpointResponse(many=True))
    def get(self):
        """
        API (GET) method to get all the info from all the users
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by the superuser

        :return: A dictionary with the user data and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        return self.get_list()


class UserDetailsEndpoint(BaseMetaResource):
    """
    Endpoint use to get the information of one single user
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = UserModel

    @doc(description="Get a user", tags=["Users"])
    @authenticate(auth_class=Auth())
    @marshal_with(UserDetailsEndpointResponse)
    @BaseMetaResource.get_data_or_404
    def get(self, user_id):
        """

        :param int user_id: User id.
        :return:
        :rtype: Tuple(dict, integer)
        """
        if self.get_user_id() != user_id and not self.is_admin():
            raise InvalidUsage(
                error="You have no permission to access given user", status_code=400
            )

        return self.get_detail(idx=user_id)

    @doc(description="Delete a user", tags=["Users"])
    @authenticate(auth_class=Auth())
    def delete(self, user_id):
        """

        :param int user_id: User id.
        :return:
        :rtype: Tuple(dict, integer)
        """
        if self.get_user_id() != user_id and not self.is_admin():
            raise NoPermission()
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist()
        # Service user can not be deleted
        if user_obj.is_service_user():
            raise NoPermission()
        log.info(f"User {user_id} was deleted by user {self.get_user_id()}")
        return self.delete_detail(idx=user_id)

    @doc(description="Edit a user", tags=["Users"])
    @authenticate(auth_class=Auth())
    @use_kwargs(UserEditRequest, location="json")
    def put(self, user_id, **data):
        """
        API method to edit an existing user.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user. Only admin and service user can edit other users.

        :param int user_id: id of the user
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        if self.get_user_id() != user_id and not self.is_admin():
            raise NoPermission()
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist()
        # in ldap-mode, users cannot be edited.
        if current_app.config["AUTH_TYPE"] == AUTH_LDAP and user_obj.comes_from_ldap():
            raise EndpointNotImplemented("To edit a user, go to LDAP server")

        if data.get("password"):
            check, msg = check_password_pattern(data.get("password"))
            if not check:
                raise InvalidCredentials(msg)

        if data.get("email"):
            check, msg = check_email_pattern(data.get("email"))
            if not check:
                raise InvalidCredentials(msg)

        log.info(f"User {user_id} was edited by user {self.get_user_id()}")
        return self.put_detail(data=data, idx=user_id, track_user=False)


class ToggleUserAdmin(BaseMetaResource):
    """
    Endpoint to convert a user into and admin or to revoke admin privileges from a suer
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    @doc(description="Toggle user into admin", tags=["Users"])
    @authenticate(auth_class=Auth())
    @marshal_with(UserEndpointResponse)
    def put(self, user_id, make_admin):
        """
        API method to make admin or take out privileges.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user. Only an admin can change this.

        :param int user_id: id of the user
        :param make_admin: 0 if the user is not going to be made admin, 1 if the user has to be made admin
        :return: A dictionary with a message (error if authentication failed, or the execution does not exist or
          a message) and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist()
        if make_admin:
            UserRoleModel(data={"user_id": user_id, "role_id": ADMIN_ROLE}).save()
        else:
            UserRoleModel.query.filter_by(user_id=user_id, role_id=ADMIN_ROLE).delete()
            try:
                db.session.commit()
            except IntegrityError as e:
                db.session.rollback()
                log.error(f"Integrity error on privileges: {e}")
            except DBAPIError as e:
                db.session.rollback()
                log.error(f"Unknown error on privileges: {e}")

        return user_obj, 200


class RecoverPassword(RecoverPasswordBaseEndpoint):
    """
    Endpoint to recover the password
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel

    @doc(description="Send email to create new password", tags=["Users"])
    @use_kwargs(RecoverPasswordRequest)
    def put(self, **kwargs):
        """
        API method to send an email to the user if they forgot to password.
        Sends a temporary password and updates the database.
        :param kwargs: a dictionary containing the email address
        :return: A dictionary with a message (error if the email address is not in the database) and an integer with
            the HTTP status code.
        :rtype: Tuple(dict, integer)
        """

        response, status = self.recover_password(kwargs.get("email"))

        log.info(f"User with email {kwargs.get('email')} has requested a new password")
        return response, status
