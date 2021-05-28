from marshmallow import fields, Schema
from .execution import ExecutionSchema, ExecutionDetailsEndpointResponse
from .common import QueryFilters


class QueryFiltersInstance(QueryFilters):
    pass


class InstanceSchema(Schema):
    """ """

    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=True, load_only=True)
    data = fields.Raw(required=True)
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    executions = fields.Nested(ExecutionSchema, many=True)
    data_hash = fields.Str(dump_only=True)


class InstanceRequest(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    data = fields.Raw(required=True)
    data_schema = fields.Str(required=False)
    schema = fields.Str(required=False)


class InstanceFileRequest(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    minimize = fields.Boolean(required=False)


class InstanceEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()


class InstanceEndpointResponse(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime()
    user_id = fields.Int()
    data_hash = fields.Str()
    schema = fields.Str(required=False)


class InstanceDetailsEndpointResponse(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    created_at = fields.Str()
    user_id = fields.Int()
    executions = fields.List(fields.Nested(ExecutionDetailsEndpointResponse))
    data_hash = fields.Str()
    schema = fields.Str(required=False)


class InstanceDataEndpointResponse(Schema):
    id = fields.Str()
    name = fields.Str()
    data = fields.Raw(required=True)
    data_hash = fields.Str()
    schema = fields.Str(required=False)
