from marshmallow import fields, Schema
from ..schemas.instance import InstanceSchema


class UserSchema(Schema):
    """

    """
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    admin = fields.Boolean(required=False, default=False)
    super_admin = fields.Boolean(required=False, load_only=True, default=False)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    instances = fields.Nested(InstanceSchema, many=True)
