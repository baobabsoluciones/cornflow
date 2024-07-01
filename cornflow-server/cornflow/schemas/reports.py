# Imports from libraries
from marshmallow import fields, Schema

# Imports from internal modules
from .common import BaseQueryFilters


class QueryFiltersReports(BaseQueryFilters):
    execution_id = fields.Str(required=False)


class ReportSchemaBase(Schema):
    id = fields.Int(dump_only=True)
    file_url = fields.Str(required=True)
    name = fields.Str(required=True)


class ReportSchema(ReportSchemaBase):
    user_id = fields.Int(required=False, load_only=True)
    execution_id = fields.Str(required=True)
    description = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)


class ReportEditRequest(Schema):
    name = fields.Str()
    description = fields.Str()
    file_url = fields.Str()


class ReportRequest(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    execution_id = fields.Str(required=True)
    file_url = fields.Str(required=True)
