from ..schemas.execution import *
from ..schemas.model_json import DataSchema


class InstanceSchema(Schema):
    """

    """
    id = fields.Str(dump_only=True)
    # TODO: required=True for user_id?
    user_id = fields.Int(required=False, load_only=True)
    data = fields.Nested(DataSchema, required=True)
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)
    executions = fields.Nested(ExecutionSchema, many=True)