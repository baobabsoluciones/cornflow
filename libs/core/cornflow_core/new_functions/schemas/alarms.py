"""
This file contains the schemas used for the table alarms defined in the application None
"""
from marshmallow import fields, Schema


class AlarmsEditRequest(Schema):
    name = fields.Str(required=False)
    criticality = fields.Number(required=False)
    description = fields.Str(required=False)


class AlarmsPostRequest(Schema):
    id = fields.Number(required=True)
    name = fields.Str(required=True)
    criticality = fields.Number(required=True)
    description = fields.Str(required=True)


class AlarmsPostBulkRequest(Schema):
    data = fields.List(fields.Nested(AlarmsPostRequest), required=True)


class AlarmsPutBulkRequestOne(AlarmsEditRequest):
    id = fields.Int(required=True)


class AlarmsPutBulkRequest(Schema):
    data = fields.List(fields.Nested(AlarmsPutBulkRequestOne), required=True)


class AlarmsResponse(AlarmsPostRequest):
    pass
