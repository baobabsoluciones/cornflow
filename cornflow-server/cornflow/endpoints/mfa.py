"""
Endpoints to manage the two-factor authentication (TOTP) of the users.

The enrollment flow is:

1. POST /mfa/setup/ generates a new TOTP secret for the user and returns it
   together with the otpauth:// provisioning URI so the client can render a
   QR code. The secret is stored encrypted at rest.
2. The user scans the QR code with their authenticator app of choice and
   sends a first code to POST /mfa/verify/. If the code is valid, MFA is
   activated, a set of one-time backup codes is generated (returned in plain
   text only this once) and a full session token is issued.

Both endpoints accept either a regular session token or the temporary
enrollment token issued by the login endpoint when MFA is required but the
user has not enrolled yet.

DELETE /user/<user_id>/mfa/ resets the MFA of a user (self service or admin,
e.g. when a phone is lost). On deployments where MFA is required the user
will be asked to enroll again at their next login.
"""

# Imports from external libraries
import secrets

import pyotp
from flask import current_app
from flask_apispec import doc, use_kwargs

# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import MFABackupCodeModel, UserModel
from cornflow.schemas.user import MFAVerifyRequest
from cornflow.shared import db
from cornflow.shared.audit import audit
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.shared.exceptions import (
    EndpointNotImplemented,
    InvalidCredentials,
    InvalidUsage,
    NoPermission,
    ObjectDoesNotExist,
)


class MFASetupEndpoint(BaseMetaResource):
    """
    Endpoint to start the two-factor authentication enrollment of a user.
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth

    @doc(description="Start the two-factor authentication enrollment", tags=["Users"])
    @authenticate(auth_class=Auth())
    def post(self, **kwargs):
        """
        API (POST) method to generate a new TOTP secret for the user.

        :return: a dict with the plain secret and the otpauth provisioning
          URI to render the QR code, and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = self.get_user()
        if user.comes_from_external_provider():
            raise EndpointNotImplemented(
                "Two-factor authentication is managed by the external "
                "identity provider",
                log_txt=f"Error while user {user.id} tries to set up MFA. "
                f"The user comes from an external provider.",
            )
        if user.mfa_enabled:
            raise InvalidUsage(
                "Two-factor authentication is already enabled. "
                "Reset it before enrolling again.",
                log_txt=f"Error while user {user.id} tries to set up MFA. "
                f"MFA is already enabled.",
            )

        secret = pyotp.random_base32()
        user.set_totp_secret(secret)
        user.save()

        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email or user.username,
            issuer_name=current_app.config["SERVICE_NAME"],
        )
        current_app.logger.info(f"User {user.id} started MFA enrollment")
        return {"secret": secret, "provisioning_uri": provisioning_uri}, 200


class MFAVerifyEndpoint(BaseMetaResource):
    """
    Endpoint to verify the first TOTP code and activate the two-factor
    authentication of a user.
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = UserModel
        self.auth_class = Auth

    @doc(description="Verify and activate two-factor authentication", tags=["Users"])
    @authenticate(auth_class=Auth())
    @use_kwargs(MFAVerifyRequest, location="json")
    def post(self, **kwargs):
        """
        API (POST) method to verify the first TOTP code. On success MFA gets
        activated, the one-time backup codes are generated and a full session
        token is returned.

        :return: a dict with the backup codes, a session token and the user
          id, and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        user = self.get_user()
        if not user.totp_secret:
            raise InvalidUsage(
                "Two-factor authentication enrollment has not been started",
                log_txt=f"Error while user {user.id} tries to verify MFA. "
                f"There is no TOTP secret stored.",
            )
        if user.mfa_enabled:
            raise InvalidUsage(
                "Two-factor authentication is already enabled",
                log_txt=f"Error while user {user.id} tries to verify MFA. "
                f"MFA is already enabled.",
            )
        if not user.check_totp_code(
            kwargs.get("totp_code"), enforce_replay=False
        ):
            raise InvalidCredentials(
                "Invalid two-factor authentication code",
                log_txt=f"Error while user {user.id} tries to verify MFA. "
                f"The code is not valid.",
            )

        number_of_codes = int(current_app.config.get("MFA_BACKUP_CODES_NUMBER", 8))
        backup_codes = [secrets.token_hex(5) for _ in range(number_of_codes)]
        MFABackupCodeModel.delete_all_for_user(user.id)
        for code in backup_codes:
            MFABackupCodeModel({"user_id": user.id, "code": code}).save()

        user.mfa_enabled = True
        user.save()

        token = self.auth_class.generate_token(user.id)
        current_app.logger.info(f"User {user.id} completed MFA enrollment")
        audit("mfa.enrolled", actor_id=user.id, actor=user.username)
        return {"backup_codes": backup_codes, "token": token, "id": user.id}, 200


class UserMFAResetEndpoint(BaseMetaResource):
    """
    Endpoint to reset (disable) the two-factor authentication of a user.
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = UserModel

    @doc(description="Reset the two-factor authentication of a user", tags=["Users"])
    @authenticate(auth_class=Auth())
    def delete(self, user_id):
        """
        API (DELETE) method to reset the MFA enrollment of a user. Only the
        user themselves or an admin can do it.

        :param int user_id: the id of the user to reset
        :return: a message and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        if self.get_user_id() != user_id and not self.is_admin():
            raise NoPermission(
                log_txt=f"Error while user {self.get_user()} tries to reset "
                f"the MFA of user {user_id}. The user does not have permission."
            )
        user_obj = UserModel.get_one_user(user_id)
        if user_obj is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to reset "
                f"the MFA of user {user_id}. The user does not exist."
            )
        user_obj.set_totp_secret(None)
        user_obj.mfa_enabled = False
        MFABackupCodeModel.delete_all_for_user(user_id)
        # Resetting the MFA revokes every outstanding session and API key
        user_obj.revoke_all_sessions()
        user_obj.api_key_version = (user_obj.api_key_version or 0) + 1
        user_obj.save()
        current_app.logger.info(
            f"The MFA of user {user_id} was reset by user {self.get_user()}"
        )
        audit(
            "mfa.reset",
            target_id=user_id,
            target=user_obj.username,
            self_service=(self.get_user_id() == user_id) or None,
        )
        return {"message": "The two-factor authentication has been reset"}, 200
