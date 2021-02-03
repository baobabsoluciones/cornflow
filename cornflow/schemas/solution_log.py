from marshmallow import fields, Schema

options = dict(required=True, allow_none=True)
pg_options = dict(many=True, required=True)

class MatrixSchema(Schema):
    constraints = fields.Int(required=False)
    variables = fields.Int(required=False)
    nonzeros = fields.Int(required=False)


class PresolveSchema(Schema):
    cols = fields.Int(required=True)
    rows = fields.Int(required=True)
    time = fields.Float(required=True)


class ProgressSchema(Schema):
    Node = fields.Str(**pg_options)
    NodesLeft = fields.Str(**pg_options)
    Objective = fields.Str(**pg_options)
    IInf = fields.Str(**pg_options)
    BestInteger = fields.Str(**pg_options)
    CutsBestBound = fields.Str(**pg_options)
    ItpNode = fields.Str(**pg_options)
    Gap = fields.Str(**pg_options)
    Time = fields.Str(**pg_options)


class Cuts(Schema):
    # TODO: this
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


class LogSchema(Schema):
    version = fields.Str(**options)
    solver = fields.Str(**options)
    status = fields.Str(**options)
    best_bound = fields.Float(**options)
    best_solution = fields.Float(**options)
    gap = fields.Float(**options)
    time = fields.Float(**options)
    matrix = fields.Nested(MatrixSchema, **options)
    matrix_post = fields.Nested(MatrixSchema, **options)
    rootTime = fields.Float(**options)
    presolve = fields.Nested(PresolveSchema, **options)
    first_relaxed = fields.Float(**options)
    first_solution = fields.Nested(FirstSolution, **options)
    status_code = fields.Int(**options)
    sol_code = fields.Int(**options)
    nodes = fields.Int(**options)
    progress = fields.Nested(ProgressSchema, required=True)
    cut_info = fields.Nested(CutInfo, **options)
