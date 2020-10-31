from marshmallow import fields, Schema
from ..schemas.model_schema_json import DataSchema
from ..schemas.log_schema import LogSchema


class OptionsSchema(Schema):
    option1 = fields.Str(required=True, many=True)


class ConfigSchema(Schema):
    solver = fields.Str(default="PULP_CBC_CMD")
    mip = fields.Boolean(required=False)
    msg = fields.Boolean(required=False)
    warmStart = fields.Boolean(required=False)
    timeLimit = fields.Integer(required=False)
    options = fields.List(fields.Str, required=False, many=True)
    keepFiles = fields.Boolean(required=False)
    gapRel = fields.Float(required=False)
    gapAbs = fields.Float(required=False)
    maxMemory = fields.Integer(required=False)
    maxNodes = fields.Integer(required=False)
    threads = fields.Integer(required=False)
    logPath = fields.Str(required=False)


class ExecutionSchema(Schema):
    id = fields.Int(dump_only=True, load_only=True)
    user_id = fields.Int(required=False, load_only=True)
    instance_id = fields.Int(required=False, dump_only=True, load_only=True)
    instance = fields.Str(required=True)
    config = fields.Nested(ConfigSchema, required=True)
    reference_id = fields.Str(dump_only=True)
    execution_results = fields.Nested(DataSchema, dump_only=True)
    log_text = fields.Str(dump_only=True)
    log_json = fields.Nested(LogSchema, dump_only=True)
    finished = fields.Boolean(required=False)
    created_at = fields.DateTime(dump_only=True)
    modified_at = fields.DateTime(dump_only=True)