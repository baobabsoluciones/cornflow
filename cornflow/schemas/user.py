from marshmallow import fields, Schema
from .instance import InstanceSchema


class UserSchema(Schema):
    """ """

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    admin = fields.Boolean(required=False, default=False, dump_only=True)
    super_admin = fields.Boolean(required=False, dump_only=True, default=False)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    instances = fields.Nested(InstanceSchema, many=True)


class UserEndpointResponse(Schema):
    id = fields.Integer()
    admin = fields.Boolean(default=False)
    super_admin = fields.Boolean(default=False)
    name = fields.String()
    email = fields.String()
    created_at = fields.String()


class UserDetailsEndpointResponse(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.String()
    admin = fields.Boolean(default=False)


class LoginEndpointRequest(Schema):
    email = fields.String(required=True)
    password = fields.String(required=True)


class UserEditRequest(Schema):
    name = fields.String(required=False)
    email = fields.String(required=False)


class UserSignupRequest(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
