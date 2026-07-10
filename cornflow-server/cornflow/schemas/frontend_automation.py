from marshmallow import Schema, fields


class FrontendAutomationQuerySchema(Schema):
    schema = fields.Str(required=False, allow_none=False)
