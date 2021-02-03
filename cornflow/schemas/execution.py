from marshmallow import fields, Schema, validate
from ..schemas.model_json import DataSchema
from ..schemas.solution_log import LogSchema
from ..shared.const import MIN_EXECUTION_STATUS_CODE, MAX_EXECUTION_STATUS_CODE


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
    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=False, load_only=True)
    instance_id = fields.Str(required=True)
    name = fields.Str()
    description = fields.Str()
    dag_run_id = fields.Str(required=False, dump_only=True)
    config = fields.Nested(ConfigSchema, required=True)
    execution_results = fields.Nested(DataSchema, dump_only=True)
    log_text = fields.Str(dump_only=True)
    log_json = fields.Nested(LogSchema, dump_only=True)
    finished = fields.Boolean(required=False)
    state = fields.Int(validate=validate.Range(min=MIN_EXECUTION_STATUS_CODE, max=MAX_EXECUTION_STATUS_CODE),
                       required=False)
    state_message = fields.Str(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class ExecutionRequest(Schema):
    config = fields.Nested(ConfigSchema)
    name = fields.String(required=True)
    description = fields.String()
    instance_id = fields.String(required=True)
    dag_name = fields.Str(default='solve_model_dag')


class ExecutionEditRequest(Schema):
    name = fields.String()
    description = fields.String()


class ExecutionDagRequest(Schema):
    execution_results = fields.Nested(DataSchema, required=True)
    log_text = fields.Str(required=True)
    log_json = fields.Nested(LogSchema, required=True)


class ExecutionDetailsEndpointResponse(Schema):
    id = fields.String()
    config = fields.Nested(ConfigSchema)
    name = fields.String()
    description = fields.String()
    created_at = fields.String()
    instance_id = fields.String()
    state = fields.Int()
    message = fields.Str(attribute='state_message')


class ExecutionStatusEndpointResponse(Schema):
    id = fields.String()
    state = fields.Int()
    message = fields.Str(attribute='state_message')


class ExecutionDataEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    data = fields.Nested(DataSchema, attribute='execution_results')


class ExecutionLogEndpointResponse(Schema):
    id = fields.String()
    name = fields.String()
    log = fields.Nested(LogSchema, attribute='log_json')
