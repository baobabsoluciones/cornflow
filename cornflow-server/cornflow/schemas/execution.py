# Imports from libraries
from marshmallow import fields, Schema, validate

# Imports from internal modules
from cornflow.shared.const import MIN_EXECUTION_STATUS_CODE, MAX_EXECUTION_STATUS_CODE
from .common import QueryFilters, BaseDataEndpointResponse
from .solution_log import LogSchema, BasicLogSchema


class QueryFiltersExecution(QueryFilters):
    pass
    # status = fields.Int(required=False)


class ConfigSchema(Schema):
    solver = fields.Str(
        dump_default="PULP_CBC_CMD", load_default="PULP_CBC_CMD", required=False
    )
    mip = fields.Boolean(required=False)
    msg = fields.Boolean(required=False)
    warmStart = fields.Boolean(required=False)
    timeLimit = fields.Int(required=False)
    seconds = fields.Int(required=False)
    options = fields.List(fields.Str, required=False, many=True)
    keepFiles = fields.Boolean(required=False)
    gapRel = fields.Float(required=False)
    gapAbs = fields.Float(required=False)
    maxMemory = fields.Int(required=False)
    maxNodes = fields.Int(required=False)
    threads = fields.Int(required=False)
    logPath = fields.Str(required=False)
    MIPGap = fields.Float(required=False)


class ConfigSchemaResponse(ConfigSchema):
    checks_only = fields.Boolean(required=False)


class ExecutionSchema(Schema):
    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=False, load_only=True)
    instance_id = fields.Str(required=True)
    name = fields.Str()
    description = fields.Str()
    schema = fields.Str(required=False)
    dag_run_id = fields.Str(required=False, dump_only=True)
    config = fields.Nested(ConfigSchema, required=True)
    data = fields.Raw(dump_only=True)
    checks = fields.Raw(required=False, allow_none=True)
    log_text = fields.Str(dump_only=True)
    log_json = fields.Nested(LogSchema, dump_only=True)
    state = fields.Int(
        validate=validate.Range(
            min=MIN_EXECUTION_STATUS_CODE, max=MAX_EXECUTION_STATUS_CODE
        ),
        required=False,
    )
    state_message = fields.Str(required=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class ExecutionRequest(Schema):
    config = fields.Raw(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    instance_id = fields.Str(required=True)
    schema = fields.Str(required=False)
    data = fields.Raw(required=False)


class ReLaunchExecutionRequest(Schema):
    config = fields.Nested(ConfigSchema, required=True)


class ExecutionEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    data = fields.Raw()


class ExecutionDagRequest(Schema):
    # TODO: change name of solution_schema
    data = fields.Raw(required=False)
    log_text = fields.Str(required=False)
    log_json = fields.Nested(LogSchema, required=False)
    state = fields.Int(required=False)
    checks = fields.Raw(required=False)
    solution_schema = fields.Str(required=False, allow_none=True)


class ExecutionDagPostRequest(ExecutionRequest, ExecutionDagRequest):
    pass


class ExecutionDetailsEndpointResponse(BaseDataEndpointResponse):
    config = fields.Raw()
    instance_id = fields.Str()
    state = fields.Int()
    message = fields.Str(attribute="state_message")


class ExecutionDetailsEndpointWithIndicatorsResponse(ExecutionDetailsEndpointResponse):
    def get_indicators(self, obj):
        indicators_string = ""
        if obj.data is not None and isinstance(obj.data, dict):
            if "indicators" in obj.data.keys():
                temp = obj.data["indicators"]
                for key, val in sorted(temp.items()):
                    indicators_string = f"{indicators_string} {key}: {val};"
        return indicators_string[1:-1]

    indicators = fields.Method("get_indicators")
    updated_at = fields.DateTime(dump_only=True)

    def get_username(self, obj):
        if hasattr(obj, "user") and obj.user is not None:
            return obj.user.username
        return None

    username = fields.Method("get_username")


class ExecutionDetailsWithIndicatorsAndLogResponse(
    ExecutionDetailsEndpointWithIndicatorsResponse
):
    log = fields.Nested(BasicLogSchema, attribute="log_json")


class ExecutionStatusEndpointResponse(Schema):
    id = fields.Str()
    state = fields.Int()
    message = fields.Str(attribute="state_message")
    data_hash = fields.Str(dump_only=True)


class ExecutionStatusEndpointUpdate(Schema):
    id = fields.Str()
    status = fields.Int()


class ExecutionDataEndpointResponse(ExecutionDetailsEndpointResponse):
    data = fields.Raw()
    checks = fields.Raw()
    log = fields.Nested(BasicLogSchema, attribute="log_json")


class ExecutionLogEndpointResponse(ExecutionDetailsEndpointWithIndicatorsResponse):
    log = fields.Nested(LogSchema, attribute="log_json")
    log_text = fields.Str(attribute="log_text")
