from marshmallow import fields, Schema


class HealthResponse(Schema):

    cornflow_status = fields.Str()
    airflow_status = fields.Str()
