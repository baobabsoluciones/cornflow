from marshmallow import fields, Schema


class DataCheckRequest(Schema):
    name = fields.Str(required=True)


class DataCheckExecutionRequest(DataCheckRequest):
    execution_id = fields.Str(required=True)


class DataCheckInstanceRequest(DataCheckRequest):
    instance_id = fields.Str(required=True)


class DataCheckCaseRequest(DataCheckRequest):
    case_id = fields.Int(required=True)
