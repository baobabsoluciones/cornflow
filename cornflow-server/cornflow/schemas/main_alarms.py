"""
This file contains the schemas used for the table main_alarms defined in the application None
"""
from marshmallow import fields, Schema


class MainAlarmsPostRequest(Schema):
    id_alarm = fields.Int(required=True)
    criticality = fields.Number(required=True)
    message = fields.Str(required=True)
    schema = fields.Str(required=False)


class MainAlarmsResponse(MainAlarmsPostRequest):
    id = fields.Int(required=True)


class QueryFiltersMainAlarms(Schema):
    schema = fields.Str(required=False)
    id_alarm = fields.Int(required=False)
    criticality = fields.Number(required=False)
