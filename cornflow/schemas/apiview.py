"""
This file contains the schemas used for the api views defined in the application
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class ApiViewResponse(Schema):
    """
    Schema for the get methods
    """

    id = fields.Int()
    name = fields.Function(lambda obj: obj.name.replace("_", " "))
    url_rule = fields.Str()
    description = fields.Str()
