"""
File with the common schemas used in cornflow
"""
from marshmallow import fields, Schema
from cornflow_core.schemas import BaseQueryFilters


class QueryFilters(BaseQueryFilters):
    schema = fields.Str(required=False)


class BaseDataEndpointResponse(Schema):
    id = fields.Str(required=True)
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime()
    user_id = fields.Int(required=True)
    data_hash = fields.Str()
    schema = fields.Str(required=False)
    updated_at = fields.DateTime()
    deleted_at = fields.DateTime()
    user_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    email = fields.Str(required=True)
    role_id = fields.Int(required=True)
    url_rule = fields.Str(required=True)
    description = fields.Str(required=True)

