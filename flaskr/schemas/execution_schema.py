from marshmallow import fields, Schema
from ..schemas.model_schema_json import DataSchema

options = dict(required=True, allow_none=True)

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

class MatrixSchema(Schema):
    constraints = fields.Int(required=False)
    variables = fields.Int(required=False)
    nonzeros = fields.Int(required=False)

class PresolveSchema(Schema):
    cols = fields.Int(required=True)
    rows = fields.Int(required=True)
    time = fields.Float(required=True)

class LogSchema(Schema):
    version = fields.Str(**options)
    solver = fields.Str(**options)
    status = fields.Str(**options)
    best_bound = fields.Float(**options)
    best_solution = fields.Float(**options)
    gap = fields.Float(**options)
    time = fields.Float(**options)
    matrix = fields.Nested(MatrixSchema, **options, many=False)
    matrix_post = fields.Nested(MatrixSchema, **options, many=False)
    rootTime = fields.Float(**options)
    presolve = fields.Nested(PresolveSchema, **options, many=False)
    first_relaxed = fields.Float(**options)
    first_solution = fields.Float(**options)
    status_code = fields.Int(**options)
    sol_code = fields.Int(**options)
    nodes = fields.Int(**options)

    # TODO: these two are incorrect:
    cut_info = fields.Int(**options)
    progress = fields.Int(**options)


class ExecutionSchema(Schema):
    """

    """
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