"""
This file contains the schemas used for the roles and roles assignations defined in the application
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class RolesRequest(Schema):
    """
    Schema used in the post methods
    """

    name = fields.Str()


class RolesResponse(RolesRequest):
    """
    Schema used in the get and put methods. Inherits the rest of the fields from :class:`RolesRequest`
    """

    id = fields.Int()
