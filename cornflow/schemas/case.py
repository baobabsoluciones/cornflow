from marshmallow import fields, Schema


class CaseBase(Schema):
    """ """

    id = fields.Int()
    path = fields.Str()
    name = fields.Str()
    description = fields.Str()
    data = fields.Raw()
    data_hash = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    deleted_at = fields.DateTime()
    solution = fields.Raw()
    solution_hash = fields.String()
    schema = fields.String()


class CaseRawData(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.String(required=True)
    path = fields.Str(required=True)
    data = fields.Raw(required=True)
    solution = fields.Raw()


class CaseSchema(Schema):
    """ """

    id = fields.Int(required=True)


class CaseRequest(Schema):
    """ """

    pass


class CaseFromInstanceExecution(Schema):
    """ """

    instance_id = fields.Str()
    execution_id = fields.Str()
    name = fields.Str(required=True)
    description = fields.Str()
    path = fields.Str(required=True)
