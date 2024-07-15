from marshmallow import fields, Schema


class ExampleListData(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)


class ExampleDetailData(ExampleListData):
    instance = fields.Raw(required=True)
    solution = fields.Raw(required=False)
