from marshmallow import fields, Schema


class ConstantSchema(Schema):
    code = fields.Int()
    name = fields.Str()
    message = fields.Str()


class ConstantsResponse(Schema):
    execution_states = fields.List(fields.Nested(ConstantSchema))
    solution_status = fields.List(fields.Nested(ConstantSchema))
    solver_status = fields.List(fields.Nested(ConstantSchema))
    execution_files_status = fields.List(fields.Nested(ConstantSchema))
