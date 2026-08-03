"""
This file contains the schemas used for the users defined in the application
"""

from marshmallow import fields, Schema, validate, validates_schema, ValidationError

from cornflow.shared.const import API_KEY_SCOPES
from .instance import InstanceSchema


class UserSchema(Schema):
    """ """

    id = fields.Int(dump_only=True)
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    instances = fields.Nested(InstanceSchema, many=True)


class UserEndpointResponse(Schema):
    id = fields.Int()
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    email = fields.Str()
    created_at = fields.Str()
    pwd_last_change = fields.DateTime()
    pwd_change_required = fields.Boolean()
    mfa_enabled = fields.Boolean()
    locked = fields.Boolean()
    last_login_at = fields.DateTime()


class UserDetailsEndpointResponse(Schema):
    id = fields.Int()
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str()
    email = fields.Str()
    pwd_last_change = fields.DateTime()
    pwd_change_required = fields.Boolean()
    mfa_enabled = fields.Boolean()
    locked = fields.Boolean()
    last_login_at = fields.DateTime()


class TokenEndpointResponse(Schema):
    valid = fields.Int()


class RecoverPasswordRequest(Schema):
    email = fields.Str(required=True)


class ResetPasswordRequest(Schema):
    """
    Schema for the request that sets a new password with a reset link token
    """

    password = fields.Str(required=True, load_only=True)


class UserEditRequest(Schema):
    username = fields.Str(required=False)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
    email = fields.Str(required=False)
    password = fields.Str(required=False)
    # Required (and verified) when a user changes their own password
    current_password = fields.Str(required=False, load_only=True)


class LoginEndpointRequest(Schema):
    """
    This is the schema used by the login endpoint with auth db or ldap
    """

    username = fields.Str(required=True)
    password = fields.Str(required=True)
    # TOTP or backup code, needed when the user has two-factor
    # authentication enabled
    totp_code = fields.Str(required=False, load_only=True)


class MFAVerifyRequest(Schema):
    """
    Schema for the request that verifies the first TOTP code and activates
    the two-factor authentication
    """

    totp_code = fields.Str(required=True, load_only=True)


class ApiKeyRequest(Schema):
    """
    Schema for the personal API key generation request. The TOTP code is the
    optional step-up second factor when the user has MFA enabled.
    """

    totp_code = fields.Str(required=False, load_only=True)
    # "full" (default) or "read" for a read-only key
    scope = fields.Str(
        required=False,
        load_only=True,
        validate=validate.OneOf(API_KEY_SCOPES),
    )


class ApiKeyResponse(Schema):
    api_key = fields.Str()
    expires_at = fields.DateTime()
    scope = fields.Str()


class LoginOpenAuthRequest(Schema):
    """
    Schema for the login request with OpenID authentication
    """
    username = fields.String(required=False)
    password = fields.String(required=False)


class SignupRequest(Schema):
    """
    This is the schema used by the sign up
    """

    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
