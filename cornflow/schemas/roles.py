"""

"""
# Imports from marshmallow library
from marshmallow import fields, Schema


class RolesRequest(Schema):
    name = fields.Str()


class RolesResponse(RolesRequest):
    id = fields.Int()
