"""
This file contains the schemas used to validate the incoming data to the different cases endpoints
and to serialize the response data given by the same endpoints.
"""

# Imports from marshmallow library
from marshmallow import fields, Schema

# Import from internal modules
from .common import BaseDataEndpointResponse, QueryFilters
from .patch import BasePatchOperation


class CaseRawRequest(Schema):

    name = fields.Str(required=True)
    description = fields.Str()
    schema = fields.Str(required=True)
    parent_id = fields.Int(allow_none=True)
    data = fields.Raw()
    checks = fields.Raw(required=False)
    solution = fields.Raw(allow_none=True, dump_default=None)
    solution_checks = fields.Raw(required=False, allow_none=True)


class CaseListResponse(BaseDataEndpointResponse):
    id = fields.Int()
    solution_hash = fields.Str()
    path = fields.Str()
    updated_at = fields.DateTime()
    dependents = fields.List(fields.Int())
    is_dir = fields.Function(
        lambda obj: obj.data is None, deserialize=lambda v: bool(v)
    )


class CaseListAllWithIndicators(CaseListResponse):
    def get_indicators(self, obj):
        indicators_string = ""
        if obj.solution is not None and isinstance(obj.solution, dict):
            if "indicators" in obj.solution.keys():
                temp = obj.solution["indicators"]
                for key, val in sorted(temp.items()):
                    indicators_string = f"{indicators_string} {key}: {val};"
        return indicators_string[1:-1]

    indicators = fields.Method("get_indicators")


class CaseBase(CaseListAllWithIndicators):
    """ """

    data = fields.Raw()
    checks = fields.Raw(required=False)
    solution = fields.Raw(required=False)
    solution_checks = fields.Raw(required=False)


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
    schema = fields.Str(required=True)


class CaseToInstanceResponse(Schema):
    """ """

    id = fields.Str(required=True)
    schema = fields.Str(required=True)


class CaseEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    parent_id = fields.Int(allow_none=True)


class CaseCompareResponse(Schema):
    data_patch = fields.Nested(BasePatchOperation, many=True)
    solution_patch = fields.Nested(BasePatchOperation, many=True)


class QueryFiltersCase(QueryFilters):
    pass


class QueryCaseCompare(Schema):
    data = fields.Boolean(required=False, dump_default=1)
    solution = fields.Boolean(required=False, dump_default=1)


class CaseCheckRequest(Schema):
    checks = fields.Raw()
    solution_checks = fields.Raw()
