from marshmallow import fields, Schema


class DeployedDAGSchema(Schema):
    """"""

    id = fields.Str(required=True)
    description = fields.Str(allow_none=True)
