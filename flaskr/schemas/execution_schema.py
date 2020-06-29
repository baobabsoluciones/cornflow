from marshmallow import fields, Schema

class OptionsSchema(Schema):
    option1 = fields.Int(required=False)

class ConfigSchema(Schema):
    solver = fields.Str(default="PULP_CBC_CMD")
    mip = fields.Boolean(required=True)
    msg = fields.Boolean(required=True)
    warmStart = fields.Boolean(required=True)
    timeLimit = fields.Integer(required=True)
    options = fields.Nested(OptionsSchema, required=True)
    keepFiles = fields.Boolean(required=True)
    gapRel = fields.Float(required=True)
    gapAbs = fields.Float(required=True)
    maxMemory = fields.Integer(required=True)
    maxNodes = fields.Integer(required=True)
    threads = fields.Integer(required=True)
    logPath = fields.Str(required=True)

class LogSchema(Schema):
    log = fields.Str(required=False)