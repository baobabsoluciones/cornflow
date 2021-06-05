"""
This file contains the schemas used for the actions defined in the application
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class ActionsResponse(Schema):
    """
    Schema used in the get methods
    """

    id = fields.Int()
    name = fields.Function(lambda obj: obj.name.replace("_", " "))
