from marshmallow import fields, Schema


class BasePatchOperation(Schema):
    op = fields.Str(required=True)
    path = fields.Str(required=True)
    value = fields.Raw()
