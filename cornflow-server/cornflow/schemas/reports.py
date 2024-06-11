# Imports from libraries
from marshmallow import fields, Schema

# Imports from internal modules
from .common import BaseQueryFilters


class QueryFiltersReports(BaseQueryFilters):
    execution_id = fields.Str(required=False)


class ReportSchema(Schema):
    id = fields.Str(dump_only=True)
    user_id = fields.Int(required=False, load_only=True)
    execution_id = fields.Str(required=True)
    name = fields.Str()
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class ReportEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    report_link = fields.Str()


class ReportRequest(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    execution_id = fields.Str(required=True)
    report_link = fields.Str(required=True)
