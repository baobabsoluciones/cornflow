"""
Schemas for the PATCH operations
"""
from marshmallow import fields, Schema


class BasePatchOperation(Schema):
    """Base structure of a JSON Patch file"""

    op = fields.Str(required=True)
    path = fields.Str(required=True)
    value = fields.Raw()
