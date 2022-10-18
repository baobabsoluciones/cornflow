from marshmallow import fields, Schema
from .execution import ExecutionSchema, ExecutionDetailsEndpointResponse
from .common import QueryFilters, BaseDataEndpointResponse


class QueryFiltersInstance(QueryFilters):
    pass


# noinspection PyTypeChecker
class InstanceSchema(Schema):
    """ """

    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=True, load_only=True)
    data = fields.Raw(required=True)
    checks = fields.Raw(required=False, allow_none=True)
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
    checks = fields.Raw(required=False, allow_none=True)
    data_schema = fields.Str(required=False)
    schema = fields.Str(required=False)


class InstanceFileRequest(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    minimize = fields.Boolean(required=False)


class InstanceEditRequest(Schema):
    name = fields.Str(required=False)
    description = fields.Str(required=False)
    data = fields.Raw(required=False)


class InstanceCheckRequest(Schema):
    checks = fields.Raw()


class InstanceEndpointResponse(BaseDataEndpointResponse):
    pass


# noinspection PyTypeChecker
class InstanceDetailsEndpointResponse(InstanceEndpointResponse):
    executions = fields.List(fields.Nested(ExecutionDetailsEndpointResponse))


class InstanceDataEndpointResponse(InstanceEndpointResponse):
    data = fields.Raw(required=True)
    checks = fields.Raw(required=False, allow_none=True)
