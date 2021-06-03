"""

"""
# Imports from marshmallow library
from marshmallow import fields, Schema


class ActionsResponse(Schema):
    id = fields.Int()
    name = fields.Function(lambda obj: obj.name.replace("_", " "))
