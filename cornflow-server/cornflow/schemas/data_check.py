from marshmallow import fields, Schema, validate


class DataCheckRequest(Schema):
    execution_id = fields.Str(required=True)
    name = fields.Str(required=True)
    config = fields.Raw(required=True)