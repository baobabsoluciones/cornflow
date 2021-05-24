from marshmallow import fields, Schema
from .execution import ExecutionSchema, ExecutionDetailsEndpointResponse

#  this import needs to be there:
from .common import QueryFilters as QueryFiltersInstance


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
    data_hash = fields.String(dump_only=True)


class InstanceRequest(Schema):
    name = fields.String(required=True)
    description = fields.String(required=False)
    data = fields.Raw(required=True)
    data_schema = fields.String(required=False)
    schema = fields.String(required=False)


class InstanceFileRequest(Schema):
    name = fields.String(required=True)
    description = fields.String(required=False)
    minimize = fields.Boolean(required=False)


class InstanceEditRequest(Schema):
    name = fields.String()
    description = fields.String()


class InstanceEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    created_at = fields.String()
    user_id = fields.Integer()
    data_hash = fields.String()
    schema = fields.String(required=False)


class InstanceDetailsEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    created_at = fields.String()
    user_id = fields.Integer()
    executions = fields.List(fields.Nested(ExecutionDetailsEndpointResponse))
    data_hash = fields.String()
    schema = fields.String(required=False)


class InstanceDataEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    data = fields.Raw(required=True)
    data_hash = fields.String()
    schema = fields.String(required=False)
