"""
This file contains the schemas used to query the results of a GET request
"""
from marshmallow import fields, Schema


class BaseQueryFilters(Schema):
    """This is the schema of the base query arguments"""

    limit = fields.Int(required=False, dump_default=20)
    offset = fields.Int(required=False, dump_default=0)
    creation_date_gte = fields.DateTime(required=False)
    creation_date_lte = fields.DateTime(required=False)
