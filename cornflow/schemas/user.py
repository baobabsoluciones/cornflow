from marshmallow import fields, Schema
from .instance import InstanceSchema


class UserSchema(Schema):
    """ """

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    # admin = fields.Boolean(required=False, default=False, dump_only=True)
    # super_admin = fields.Boolean(required=False, dump_only=True, default=False)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    instances = fields.Nested(InstanceSchema, many=True)


class UserEndpointResponse(Schema):
    id = fields.Int()
    # admin = fields.Boolean(default=False)
    # super_admin = fields.Boolean(default=False)
    name = fields.Str()
    email = fields.Str()
    created_at = fields.Str()


class UserDetailsEndpointResponse(Schema):
    id = fields.Int()
    name = fields.Str()
    email = fields.Str()
    # admin = fields.Boolean(default=False)


class LoginEndpointRequest(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)


class UserEditRequest(Schema):
    name = fields.Str(required=False)
    email = fields.Str(required=False)
    password = fields.Str(required=False)


class UserSignupRequest(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
