"""
File with the schemas used by the cases endpoints
"""
from marshmallow import fields, Schema

from .common import QueryFilters as QueryFiltersCase


class CaseRawRequest(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.Str(required=True)
    path = fields.Str(required=True)
    data = fields.Raw(required=True)
    solution = fields.Raw()


class CaseListResponse(Schema):
    id = fields.Int()
    path = fields.Str()
    name = fields.Str()
    description = fields.Str()
    data_hash = fields.Str()
    solution_hash = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    schema = fields.Str()
    dependents = fields.List(fields.Int())


class CaseBase(CaseListResponse):
    """ """

    data = fields.Raw()
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


class CaseToLive(Schema):
    """ """

    id = fields.Str(required=True)
    schema = fields.Str(required=True)


class CaseEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    schema = fields.Str()
    path = fields.Str()
