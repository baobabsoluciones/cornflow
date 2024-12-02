from marshmallow import fields, Schema, EXCLUDE

options = dict(required=True, allow_none=True)
log_options = dict(required=False, allow_none=True)
pg_options = dict(many=True, required=True)
list_of_strings = fields.List(fields.Str, required=False, many=True)


class MatrixSchema(Schema):
    constraints = fields.Int(required=False)
    variables = fields.Int(required=False)
    nonzeros = fields.Int(required=False)


class PresolveSchema(Schema):
    cols = fields.Int(required=True)
    rows = fields.Int(required=True)
    time = fields.Float(required=True)


class ProgressSchema(Schema):
    Node = list_of_strings
    NodesLeft = list_of_strings
    Objective = list_of_strings
    IInf = list_of_strings
    BestInteger = list_of_strings
    CutsBestBound = list_of_strings
    ItpNode = list_of_strings
    Gap = list_of_strings
    Time = list_of_strings
    Depth = list_of_strings


class Cuts(Schema):
    pass


class CutInfo(Schema):
    time = fields.Float()
    best_bound = fields.Float(**options)
    best_solution = fields.Float(**options)
    cuts = fields.Nested(Cuts, required=False)


class FirstSolution(Schema):
    Node = fields.Int(**options)
    NodesLeft = fields.Int(**options)
    BestInteger = fields.Float(**options)
    CutsBestBound = fields.Float(**options)


class BasicLogSchema(Schema):
    status = fields.Str(**log_options)
    status_code = fields.Int(**log_options)
    sol_code = fields.Int(**log_options)


class LogSchema(BasicLogSchema):
    class Meta:
        unknown = EXCLUDE

    version = fields.Str(**log_options)
    solver = fields.Str(**log_options)
    best_bound = fields.Float(**log_options)
    best_solution = fields.Float(**log_options)
    gap = fields.Float(**log_options)
    time = fields.Float(**log_options)
    matrix = fields.Nested(MatrixSchema, **log_options)
    matrix_post = fields.Nested(MatrixSchema, **log_options)
    rootTime = fields.Float(**log_options)
    presolve = fields.Nested(PresolveSchema, **log_options)
    first_relaxed = fields.Float(**log_options)
    first_solution = fields.Nested(FirstSolution, **log_options)
    nodes = fields.Int(**log_options)
    progress = fields.Nested(ProgressSchema, required=False)
    cut_info = fields.Raw(**log_options)
