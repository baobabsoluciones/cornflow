from marshmallow import fields, Schema


class QueryFilters(Schema):
    limit = fields.Int(required=False, default=20)
    offset = fields.Int(required=False, default=0)
    creation_date_gte = fields.DateTime(required=False)
    creation_date_lte = fields.DateTime(required=False)
