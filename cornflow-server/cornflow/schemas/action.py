"""
This file contains the schemas used for the actions defined in the application
"""

from marshmallow import fields, Schema


class ActionsResponse(Schema):
    """
    Schema used in the get methods. Used only for serialization
    """

    id = fields.Int()
    name = fields.Function(serialize=lambda obj: obj.name.replace("_", " "))
