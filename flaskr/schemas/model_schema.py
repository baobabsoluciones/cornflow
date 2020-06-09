from marshmallow import fields, Schema


class CoefficientsSchema(Schema):
    name = fields.Str(required=True)
    value = fields.Float(required=True)


class ObjectiveSchema(Schema):
    name = fields.Str(required=True)
    coefficients = fields.Nested(CoefficientsSchema, many=True, required=True)


class ConstraintSchema(Schema):
    sense = fields.Int(required=True)
    pi = fields.Float(required=False, allow_none=True)
    constant = fields.Float(required=True)
    name = fields.Str(required=True)
    coefficients = fields.Nested(CoefficientsSchema, many=True, required=True)


class VariableSchema(Schema):
    lowBound = fields.Float(allow_none=True)
    upBound = fields.Float(allow_none=True)
    cat = fields.Str(required=True)
    varValue = fields.Float(allow_none=True)
    dj = fields.Float(allow_none=True)
    name = fields.Str(required=True)


class ParametersSchema(Schema):
    name = fields.Str(required=True)
    sense = fields.Int(required=True)
    status = fields.Int()
    sol_status = fields.Int()


class Sos1Constraints(Schema):
    placeholder = fields.Str(required=False)


class Sos2Constraints(Schema):
    placeholder = fields.Str(required=False)


class DataSchema(Schema):
    objective = fields.Nested(ObjectiveSchema, required=True)
    constraints = fields.Nested(ConstraintSchema, many=True, required=True)
    variables = fields.Nested(VariableSchema, many=True, required=True)
    parameters = fields.Nested(ParametersSchema, required=True)
    sos1 = fields.Nested(Sos1Constraints, many=True, required=False)
    sos2 = fields.Nested(Sos2Constraints, many=True, required=False)
