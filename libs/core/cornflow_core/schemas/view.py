"""
This file contains the schemas used for the api views defined in the application
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class ViewResponse(Schema):
    """
    Schema for the get methods. Used only for serialization
    """

    id = fields.Int()
    name = fields.Function(serialize=lambda obj: obj.name.replace("_", " "))
    url_rule = fields.Str()
    description = fields.Str()
