"""
This file contains the schemas used by the user model
"""
from marshmallow import fields, Schema


class BaseUserSchema(Schema):
    """ """

    id = fields.Int(dump_only=True)
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)


class LoginEndpointRequest(Schema):
    """ """

    username = fields.Str(required=True)
    password = fields.Str(required=True)


class LoginOpenAuthRequest(Schema):
    """ """

    token = fields.Str(required=True)


class SignupRequest(Schema):
    """ """

    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
