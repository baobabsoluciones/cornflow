from marshmallow import fields, Schema


class SchemaListApp(Schema):
    name = fields.Str(required=True)


class SchemaOneApp(SchemaListApp):
    instance = fields.Raw(required=True)
    solution = fields.Raw(required=True)
    config = fields.Raw(required=True)
    instance_checks = fields.Raw(required=True)
    solution_checks = fields.Raw(required=True)


class SchemaRequest(Schema):
    dag_name = fields.Str(required=True)
