"""
This file contains the schemas used by the user model
"""
from marshmallow import fields, Schema


class BaseUserSchema(Schema):
    """
    This is the base schema used for the users
    """

    id = fields.Int(dump_only=True)
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)


class LoginEndpointRequest(Schema):
    """
    This is the schema used by the login endpoint with auth db or ldap
    """

    username = fields.Str(required=True)
    password = fields.Str(required=True)


class LoginOpenAuthRequest(Schema):
    """
    This is the schema used by the login endpoint with Open ID protocol
    """

    token = fields.Str(required=True)


class SignupRequest(Schema):
    """
    This is the schema used by the sign up
    """

    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
