"""
This file contains the schemas used to query the results of a GET request
"""

from marshmallow import fields, Schema


class BaseQueryFilters(Schema):
    """This is the schema of the base query arguments"""

    limit = fields.Int(required=False, dump_default=10)
    offset = fields.Int(required=False, dump_default=0)
    creation_date_gte = fields.DateTime(required=False)
    creation_date_lte = fields.DateTime(required=False)
    id = fields.Str(required=False)
    name = fields.Str(required=False)
    deletion_date_gte = fields.DateTime(required=False)
    deletion_date_lte = fields.DateTime(required=False)
    update_date_gte = fields.DateTime(required=False)
    update_date_lte = fields.DateTime(required=False)
    user_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
    email = fields.Str(required=False)
    role_id = fields.Int(required=False)
    url_rule = fields.Str(required=False)
    description = fields.Str(required=False)
