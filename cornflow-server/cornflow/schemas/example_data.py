from marshmallow import fields, Schema


class ExampleData(Schema):
    name = fields.Str(required=True)
    examples = fields.Raw(required=True)
