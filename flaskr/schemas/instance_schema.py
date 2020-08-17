from flaskr.schemas.execution_schema import *
from flaskr.schemas.model_schema import *

class InstanceSchema(Schema):
    """

    """
    id = fields.Int(dump_only=True, load_only=True)
    user_id = fields.Int(required=False, load_only=True)
    data = fields.Nested(DataSchema, required=True, load_only=True)
    name = fields.Str(dump_only=True)
    reference_id = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)
    executions = fields.Nested(ExecutionSchema, many=True)