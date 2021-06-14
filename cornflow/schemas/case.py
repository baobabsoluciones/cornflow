"""
This file contains the schemas used to validate the incoming data to the different cases endpoints
and to serialize the response data given by the same endpoints.
"""

# Imports from marshmallow library
from marshmallow import fields, Schema

# Import from internal modules
from .common import QueryFilters, PatchOperation


class CaseRawRequest(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.Str(required=True)
    parent_id = fields.Int()
    data = fields.Raw()
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
    is_dir = fields.Function(
        lambda obj: obj.data is None, deserialize=lambda v: bool(v)
    )
    # uppername = fields.Function(lambda obj: obj.name.upper())


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
    parent_id = fields.Int()


class CaseToInstanceResponse(Schema):
    """ """

    id = fields.Str(required=True)
    schema = fields.Str(required=True)


class CaseEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    schema = fields.Str()


class CaseCompareResponse(Schema):
    data_patch = fields.Nested(PatchOperation, many=True)
    solution_patch = fields.Nested(PatchOperation, many=True)


class QueryFiltersCase(QueryFilters):
    pass


class QueryCaseCompare(Schema):
    data = fields.Boolean(required=False, default=1)
    solution = fields.Boolean(required=False, default=1)
