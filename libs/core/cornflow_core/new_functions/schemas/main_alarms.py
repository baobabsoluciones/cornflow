"""
This file contains the schemas used for the table main_alarms defined in the application None
"""
from marshmallow import fields, Schema


class MainAlarmsEditRequest(Schema):
    id_alarm = fields.Int(required=False)
    criticality = fields.Number(required=False)
    message = fields.Str(required=False)


class MainAlarmsPostRequest(Schema):
    id = fields.Number(required=True)
    id_alarm = fields.Int(required=True)
    criticality = fields.Number(required=True)
    message = fields.Str(required=True)


class MainAlarmsPostBulkRequest(Schema):
    data = fields.List(fields.Nested(MainAlarmsPostRequest), required=True)


class MainAlarmsPutBulkRequestOne(MainAlarmsEditRequest):
    id = fields.Int(required=True)


class MainAlarmsPutBulkRequest(Schema):
    data = fields.List(fields.Nested(MainAlarmsPutBulkRequestOne), required=True)


class MainAlarmsResponse(MainAlarmsPostRequest):
    pass
