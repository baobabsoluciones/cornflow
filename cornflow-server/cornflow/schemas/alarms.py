"""
This file contains the schemas used for the table alarms defined in the application None
"""

from marshmallow import fields, Schema


class AlarmsPostRequest(Schema):
    name = fields.Str(required=True)
    criticality = fields.Number(required=True)
    description = fields.Str(required=True)
    schema = fields.Str(required=False)


class AlarmsResponse(AlarmsPostRequest):
    id = fields.Int(required=True)


class QueryFiltersAlarms(Schema):
    schema = fields.Str(required=False)
    criticality = fields.Number(required=False)


class AlarmEditRequest(Schema):
    name = fields.Str(required=False)
    criticality = fields.Number(required=False)
    description = fields.Str(required=False)
    schema = fields.Str(required=False)
