from marshmallow import fields, Schema

class ConfigSchema(Schema):
    mip = fields.Boolean(required=True)
    timeLimit = fields.Integer(required=True)
    solver = fields.Str(required = True)
    mipStart = fields.Boolean(required=True)
    cores = fields.Integer(required=True)
    maxNodes= fields.Integer(required=True)
    maxMemory = fields.Integer(required=True)
    gapRel = fields.Float(required=True)
    gapAbs = fields.Float(required=True)
    keepFiles = fields.Boolean(required=True)