from marshmallow import fields, Schema

options = dict(required=True, allow_none=True)


class MatrixSchema(Schema):
    constraints = fields.Int(required=False)
    variables = fields.Int(required=False)
    nonzeros = fields.Int(required=False)


class PresolveSchema(Schema):
    cols = fields.Int(required=True)
    rows = fields.Int(required=True)
    time = fields.Float(required=True)


class ProgressDataSchema(Schema):
    row = fields.Str(many=True, required=True)


class ProgressSchema(Schema):
    columns = fields.Str(many=True)
    data = fields.Nested(ProgressDataSchema, many=True)


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
    progress = fields.Nested(ProgressSchema, required=True)

    # TODO: these two are incorrect:
    cut_info = fields.Int(**options)
