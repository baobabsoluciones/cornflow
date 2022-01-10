from marshmallow import fields, Schema


class DeployedDAGSchema(Schema):
    """"""

    id = fields.Str()
    description = fields.Str()
