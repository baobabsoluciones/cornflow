"""
This file contains the schemas used for the users defined in the application
"""

from marshmallow import fields, Schema, validates_schema, ValidationError
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
    pwd_last_change = fields.Str()


class UserDetailsEndpointResponse(Schema):
    id = fields.Int()
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str()
    email = fields.Str()
    pwd_last_change = fields.Str()


class TokenEndpointResponse(Schema):
    valid = fields.Int()


class RecoverPasswordRequest(Schema):
    email = fields.Str(required=True)


class UserEditRequest(Schema):
    username = fields.Str(required=False)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
    email = fields.Str(required=False)
    password = fields.Str(required=False)
    pwd_last_change = fields.DateTime(required=False)


class LoginEndpointRequest(Schema):
    """
    This is the schema used by the login endpoint with auth db or ldap
    """

    username = fields.Str(required=True)
    password = fields.Str(required=True)


class LoginOpenAuthRequest(Schema):
    """
    This is the schema used by the login endpoint with Open ID protocol
    Validates that either a token is provided, or both username and password are present
    """

    token = fields.Str(required=False)
    username = fields.Str(required=False)
    password = fields.Str(required=False)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        if data.get("token") is None:
            if not data.get("username") or not data.get("password"):
                raise ValidationError(
                    "A token needs to be provided when using Open ID authentication"
                )
        else:
            if data.get("username") or data.get("password"):
                raise ValidationError("The login needs to be done with a token only")


class SignupRequest(Schema):
    """
    This is the schema used by the sign up
    """

    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
