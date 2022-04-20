from marshmallow import fields, Schema


class BaseQueryFilters(Schema):
    limit = fields.Int(required=False, dump_default=20)
    offset = fields.Int(required=False, dump_default=0)
    creation_date_gte = fields.DateTime(required=False)
    creation_date_lte = fields.DateTime(required=False)
