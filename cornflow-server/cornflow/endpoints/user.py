"""
Endpoints for the user profiles
"""
# Imports from external libraries
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc
from sqlalchemy.exc import DBAPIError, IntegrityError

# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import UserModel, UserRoleModel
from cornflow.schemas.user import (
    RecoverPasswordRequest,
    UserDetailsEndpointResponse,
    UserEditRequest,
    UserEndpointResponse,
    UserSchema,
)
from cornflow.shared import db
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ADMIN_ROLE, AUTH_LDAP, ALL_DEFAULT_ROLES, AUTH_OID
from cornflow.shared.exceptions import (
    ConfigurationError,
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
    NoPermission,
    ObjectDoesNotExist,
)
from cornflow.shared.email import get_password_recover_email, send_email_to
from cornflow.shared.validators import check_email_pattern, check_password_pattern


class UserEndpoint(BaseMetaResource):
    """
    Endpoint with a get method which gives back all the info related to the users.
    Including their instances and executions
    """

    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = UserModel

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
        current_app.logger.info(f"User {self.get_user()} gets all users")
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
                error="You have no permission to access given user",
                status_code=400,
                log_txt=f"Error while user {self.get_user()} tries to get the details of user {user_id}. "
                f"The user does not have permission.",
            )
        current_app.logger.info(
            f"User {self.get_user()} gets details of user {user_id}"
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
            raise NoPermission(
                log_txt=f"Error while user {self.get_user()} tries to delete user {user_id}. "
                f"The user does not have permission."
            )
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to delete user {user_id}. "
                f"The user to delete does not exists."
            )
        # Service user can not be deleted
        if user_obj.is_service_user():
            raise NoPermission(
                log_txt=f"Error while user {self.get_user()} tries to delete user {user_id}. "
                f"The user to delete is a service user and therefore can not be deleted."
            )
        current_app.logger.info(
            f"User {user_obj.id} was deleted by user {self.get_user()}"
        )
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
            raise NoPermission(
                log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                f"The user does not have permission."
            )
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                f"The user to edit does not exist."
            )
        # working with a ldap service users cannot be edited.
        if (
            current_app.config["AUTH_TYPE"] == AUTH_LDAP
            and user_obj.comes_from_external_provider()
        ):
            raise EndpointNotImplemented(
                "To edit a user, go to LDAP server",
                log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                f"To edit a user, go to LDAP server.",
            )
        # working with an OID provider users can not be edited
        if (
            current_app.config["AUTH_TYPE"] == AUTH_OID
            and user_obj.comes_from_external_provider()
        ):
            raise EndpointNotImplemented(
                "To edit a user, go to the OID provider",
                log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                f"To edit a user, go to the OID provider.",
            )

        if data.get("password") is not None:
            check, msg = check_password_pattern(data.get("password"))
            if not check:
                raise InvalidCredentials(
                    msg,
                    log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                    f"The new password is not valid.",
                )

        if data.get("email") is not None:
            check, msg = check_email_pattern(data.get("email"))
            if not check:
                raise InvalidCredentials(
                    msg,
                    log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                    f"The new email is not valid.",
                )

        current_app.logger.info(f"User {user_id} was edited by user {self.get_user()}")
        return self.put_detail(data=data, idx=user_id, track_user=False)


class ToggleUserAdmin(BaseMetaResource):
    """
    Endpoint to convert a user into and admin or to revoke admin privileges from a user
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
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to edit user {user_id}. "
                f"The user to edit does not exist."
            )
        if make_admin:
            UserRoleModel(data={"user_id": user_id, "role_id": ADMIN_ROLE}).save()
            current_app.logger.info(f"User {user_id} was made into an admin")
        else:
            UserRoleModel.query.filter_by(user_id=user_id, role_id=ADMIN_ROLE).delete()
            current_app.logger.info(f"User {user_id} was removed admin role")
            try:
                db.session.commit()
            except IntegrityError as e:
                db.session.rollback()
                current_app.logger.error(f"Integrity error on privileges: {e}")
            except DBAPIError as e:
                db.session.rollback()
                current_app.logger.error(f"Unknown error on privileges: {e}")
        return user_obj, 200


class RecoverPassword(BaseMetaResource):
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

        sender = current_app.config["SERVICE_EMAIL_ADDRESS"]
        password = current_app.config["SERVICE_EMAIL_PASSWORD"]
        smtp_server = current_app.config["SERVICE_EMAIL_SERVER"]
        port = current_app.config["SERVICE_EMAIL_PORT"]
        service_name = current_app.config["SERVICE_NAME"]
        receiver = kwargs.get("email")

        if sender is None or password is None or smtp_server is None or port is None:
            raise ConfigurationError(
                "This functionality is not available. Check that cornflow's email is correctly configured"
            )

        message = "The password recovery process has started. Check the email inbox."

        user_obj = self.data_model({"email": receiver})
        if not user_obj.check_email_in_use():
            return {"message": message}, 200

        new_password = self.data_model.generate_random_password()

        text_email = get_password_recover_email(
            temp_password=new_password,
            service_name=service_name,
            sender=sender,
            receiver=receiver,
        )

        send_email_to(
            email=text_email,
            smtp_server=smtp_server,
            port=port,
            sender=sender,
            password=password,
            receiver=receiver,
        )

        data = {"password": new_password}
        user_obj = self.data_model.get_one_user_by_email(receiver)
        user_obj.update(data)

        current_app.logger.info(
            f"User with email {receiver} has requested a new password"
        )
        return {"message": message}, 200
