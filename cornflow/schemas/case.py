"""
This file contains the schemas used to validate the incoming data to the different cases endpoints
and to serialize the response data given by the same endpoints.
"""

# Imports from marshmallow library
from marshmallow import fields, Schema

# Import from internal modules
from .common import QueryFilters


class CaseRawRequest(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.String(required=True)
    path = fields.Str(required=True)
    data = fields.Raw(required=True)
    solution = fields.Raw()


class CaseListResponse(Schema):
    id = fields.Int()
    path = fields.Str()
    name = fields.Str()
    description = fields.Str()
    data_hash = fields.String()
    solution_hash = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    schema = fields.String()
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


class CaseToInstanceResponse(Schema):
    """ """

    id = fields.Str(required=True)
    schema = fields.Str(required=True)


class CaseEditRequest(Schema):
    name = fields.String()
    description = fields.String()
    schema = fields.String()


class QueryFiltersCase(QueryFilters):
    pass
