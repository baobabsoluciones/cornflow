"""
File with the common schemas used in cornflow
"""
from marshmallow import fields, Schema


class QueryFilters(Schema):
    limit = fields.Int(required=False, default=20)
    offset = fields.Int(required=False, default=0)
    creation_date_gte = fields.DateTime(required=False)
    creation_date_lte = fields.DateTime(required=False)
    schema = fields.Str(required=False)


class PatchOperation(Schema):
    op = fields.Str(required=True)
    path = fields.Str(required=True)
    value = fields.Raw()


class BaseDataEndpointResponse(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime()
    user_id = fields.Int()
    data_hash = fields.Str()
    schema = fields.Str(required=False)
