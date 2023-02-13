from marshmallow import fields, Schema


class TableSchema(Schema):
    data = fields.Raw(required=True)
