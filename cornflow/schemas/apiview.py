"""

"""
# Imports from marshmallow library
from marshmallow import fields, Schema


class ApiViewResponse(Schema):
    id = fields.Int()
    name = fields.Function(lambda obj: obj.name.replace("_", " "))
    url_rule = fields.Str()
    description = fields.Str()
