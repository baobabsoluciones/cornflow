"""
This file contains the schemas used to validate the incoming data to the different cases endpoints
and to serialize the response data given by the same endpoints.
"""

# Imports from marshmallow library
from marshmallow import fields, Schema

# Import from internal modules
from .common import QueryFilters, PatchOperation
from .common import BaseDataEndpointResponse


class CaseRawRequest(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.Str(required=True)
    parent_id = fields.Int(allow_none=True)
    data = fields.Raw()
    solution = fields.Raw(allow_none=True, dump_default=None)


class CaseListResponse(BaseDataEndpointResponse):
    id = fields.Int()
    solution_hash = fields.Str()
    path = fields.Str()
    updated_at = fields.DateTime()
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
    parent_id = fields.Int(allow_none=True)


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
    data = fields.Boolean(required=False, dump_default=1)
    solution = fields.Boolean(required=False, dump_default=1)
