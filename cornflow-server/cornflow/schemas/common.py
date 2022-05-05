"""
File with the common schemas used in cornflow
"""
from marshmallow import fields, Schema
from cornflow_core.schemas import BaseQueryFilters


class QueryFilters(BaseQueryFilters):
    schema = fields.Str(required=False)


class BaseDataEndpointResponse(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime()
    user_id = fields.Int()
    data_hash = fields.Str()
    schema = fields.Str(required=False)
