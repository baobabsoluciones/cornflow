"""
External endpoint for the user to log in to the cornflow webserver
"""

from datetime import datetime, timezone

# Partial imports
from flask import current_app, request
from flask_apispec import use_kwargs, doc
from sqlalchemy.exc import IntegrityError, DBAPIError

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import (
    MFABackupCodeModel,
    PermissionsDAG,
    UserModel,
    UserRoleModel,
)
from cornflow.schemas.user import LoginEndpointRequest, LoginOpenAuthRequest
from cornflow.shared import db
from cornflow.shared.audit import audit
from cornflow.shared.authentication import Auth, LDAPBase
from cornflow.shared.rate_limit import (
    limiter,
    login_rate_limit,
    RATE_LIMIT_MESSAGE,
)
from cornflow.shared.const import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OID,
    TOKEN_PURPOSE_MFA_SETUP,
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
        totp_code = kwargs.pop("totp_code", None)

        if auth_type == AUTH_DB:
            user = self.auth_db_authenticate(**kwargs)
            mfa_response = self.check_mfa(user, totp_code)
            if mfa_response is not None:
                return mfa_response, 200
            # The authentication is fully completed: clear the failed
            # login attempts counter and record the login timestamp. The
            # previous timestamp is returned so the client can show the
            # user their last access.
            user.reset_failed_login()
            response.update({"change_password": check_last_password_change(user)})
            response.update({"last_login": self._register_successful_login(user)})
            current_app.logger.info(
                f"User {user.id} logged in successfully using database authentication"
            )
            audit(
                "login.success",
                actor_id=user.id,
                actor=user.username,
                method="db",
            )
        elif auth_type == AUTH_LDAP:
            user = self.auth_ldap_authenticate(**kwargs)
            current_app.logger.info(
                f"User {user.id} logged in successfully using LDAP authentication"
            )
            audit(
                "login.success",
                actor_id=user.id,
                actor=user.username,
                method="ldap",
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
                audit(
                    "login.success",
                    actor_id=user.id,
                    actor=user.username,
                    method="oid_service",
                )
                token = self.auth_class.generate_token(user.id)
            else:
                token = self.auth_class().get_token_from_header(request.headers)
                user = self.auth_oid_authenticate(token=token)
                current_app.logger.info(
                    f"User {user.id} logged in successfully using OpenID authentication"
                )
                audit(
                    "login.success",
                    actor_id=user.id,
                    actor=user.username,
                    method="oid",
                )

            response.update({"token": token, "id": user.id})
            return response, 200
        else:
            raise ConfigurationError()

        try:
            token = self.auth_class.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(
                "Could not complete the login. Please try again or contact "
                "an administrator.",
                status_code=400,
                log_txt=f"Error while generating the token for user {user.id}: "
                f"{str(e)}",
            )

        response.update({"token": token, "id": user.id})

        return response, 200

    @staticmethod
    def _register_successful_login(user):
        """
        Stamps the current login time on the user and returns the previous
        login time (ISO string or None) so the client can display it.

        :param user: the user that just logged in
        :return: the previous last-login timestamp as ISO 8601, or None
        :rtype: str or None
        """
        previous = user.last_login_at
        user.last_login_at = datetime.now(timezone.utc)
        db.session.add(user)
        db.session.commit()
        return previous.isoformat() if previous else None

    def check_mfa(self, user, totp_code):
        """
        Handles the two-factor authentication step of the login for internal
        (database authenticated) users. Service users are exempt as they are
        machine-to-machine accounts.

        :param user: the user that passed the password authentication
        :param str totp_code: the TOTP (or backup) code sent on the login
          request, if any
        :return: None if the login can continue, or the dict that must be
          returned to the client to complete the missing MFA step
        :rtype: dict or None
        """
        if user.is_service_user():
            return None

        if user.mfa_enabled:
            if not totp_code:
                current_app.logger.info(
                    f"User {user.id} passed password authentication, "
                    f"waiting for the two-factor authentication code"
                )
                return {"mfa_required": True}
            valid = user.check_totp_code(totp_code)
            if not valid:
                valid = MFABackupCodeModel.try_consume(user.id, totp_code)
                if valid:
                    db.session.commit()
                    current_app.logger.info(
                        f"User {user.id} logged in using a backup code"
                    )
            if not valid:
                # Wrong second-factor codes also count towards the lockout
                user.register_failed_login()
                audit(
                    "login.failure",
                    outcome="failure",
                    actor_id=user.id,
                    actor=user.username,
                    reason="bad_totp",
                )
                if user.is_login_locked():
                    self.raise_account_locked(user)
                raise InvalidCredentials(
                    "Invalid two-factor authentication code",
                    log_txt=f"Error while user {user.id} tries to log in. "
                    f"The two-factor authentication code is not valid.",
                )
            return None

        if int(current_app.config.get("MFA_REQUIRED", 0)) == 1:
            temp_token = self.auth_class.generate_token(
                user.id, purpose=TOKEN_PURPOSE_MFA_SETUP
            )
            current_app.logger.info(
                f"User {user.id} passed password authentication and must "
                f"enroll in two-factor authentication"
            )
            return {"mfa_setup_required": True, "temp_token": temp_token}

        return None

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
            # The audit channel is a trusted internal sink, so recording the
            # attempted (non-existent) username is fine and useful to
            # defenders; the response to the client stays generic.
            audit(
                "login.failure",
                outcome="failure",
                actor=username,
                reason="unknown_user",
            )
            raise InvalidCredentials()

        # The password is always checked first and, on failure, the same
        # generic error is returned whether the account exists, the password
        # is wrong or the account is locked. This avoids leaking (through the
        # account-locked message) that a given username exists. The lock is
        # only revealed to a caller that provided the correct password, i.e.
        # the legitimate owner of the account.
        if not user.check_hash(password):
            user.register_failed_login()
            audit(
                "login.failure",
                outcome="failure",
                actor_id=user.id,
                actor=user.username,
                reason="bad_password",
            )
            raise InvalidCredentials()

        self.check_account_lock(user)

        return user

    @staticmethod
    def check_account_lock(user):
        """
        Raises an error if the account is locked because of too many
        consecutive failed login attempts.

        :param user: the user trying to log in
        """
        if user.is_login_locked():
            LoginBaseEndpoint.raise_account_locked(user)

    @staticmethod
    def raise_account_locked(user):
        """
        Raises the account-locked error.

        :param user: the locked user
        """
        raise InvalidCredentials(
            "The account is locked due to too many failed login attempts. "
            "Please contact a platform administrator to unlock it.",
            status_code=403,
            payload={"error_code": "account_locked"},
            log_txt=f"Error while user {user.id} tries to log in. "
            f"The account is locked.",
        )

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

                email_names = email.split("@")[0]
                if "." in email_names:
                    default_first_name, default_last_name = email_names.split(".")[0:2]
                else:
                    default_first_name, default_last_name = email_names, ""

                first_name = decoded_token.get("given_name", default_first_name)
                last_name = decoded_token.get("family_name", default_last_name)

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
    Check if the user needs to change their password, either because the
    password rotation time has passed or because the password was flagged
    for a forced change (first login after the policy hardening, a password
    reset by an admin or a recovery with a temporary password).

    :param user: The user object to check
    :return: True if password needs to be changed, False otherwise
    :rtype: bool
    """
    if user.pwd_change_required:
        return True
    return Auth.password_rotation_expired(user)


class LoginEndpoint(LoginBaseEndpoint):
    """
    Endpoint used to do the login to the cornflow webserver
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth
        self.user_role_association = UserRoleModel

    # Per-IP rate limit applied around the whole endpoint (flask-restful
    # discovers class-level decorators; a per-method decorator would not be
    # enforced through its dispatch)
    decorators = [limiter.limit(login_rate_limit, error_message=RATE_LIMIT_MESSAGE)]

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

    decorators = [limiter.limit(login_rate_limit, error_message=RATE_LIMIT_MESSAGE)]

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
