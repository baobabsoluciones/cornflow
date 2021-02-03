from marshmallow import fields, Schema

from ..schemas.execution import ExecutionSchema, ExecutionDetailsEndpointResponse
from ..schemas.model_json import DataSchema


class InstanceSchema(Schema):
    """

    """
    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=True, load_only=True)
    data = fields.Nested(DataSchema, required=True)
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    executions = fields.Nested(ExecutionSchema, many=True)


class InstanceRequest(Schema):
    name = fields.String(required=True)
    description = fields.String(required=False)
    data = fields.Nested(DataSchema, required=True)


class InstanceFileRequest(Schema):
    name = fields.String(required=True)
    description = fields.String(required=False)


class InstanceEditRequest(Schema):
    name = fields.String()
    description = fields.String()


class InstanceEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    created_at = fields.String()
    user_id = fields.Integer()


class InstanceDetailsEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    created_at = fields.String()
    user_id = fields.Integer()
    executions = fields.List(fields.Nested(ExecutionDetailsEndpointResponse))


class InstanceDataEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    data = fields.Nested(DataSchema, required=True)
