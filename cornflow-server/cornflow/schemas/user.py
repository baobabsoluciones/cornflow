from cornflow_core.schemas import BaseUserSchema
from marshmallow import fields, Schema

from .instance import InstanceSchema


class UserSchema(BaseUserSchema):
    """ """

    instances = fields.Nested(InstanceSchema, many=True)


class UserEndpointResponse(Schema):
    id = fields.Int()
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    email = fields.Str()
    created_at = fields.Str()


class UserDetailsEndpointResponse(Schema):
    id = fields.Int()
    first_name = fields.Str()
    last_name = fields.Str()
    username = fields.Str()
    email = fields.Str()


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
