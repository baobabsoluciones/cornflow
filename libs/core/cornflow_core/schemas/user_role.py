"""
This file contains the schemas used for the roles and roles assignations defined in the application
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class UserRoleRequest(Schema):
    """
    Schema used in the post methods
    """

    user_id = fields.Int()
    role_id = fields.Int()


class UserRoleResponse(UserRoleRequest):
    """
    Schema used in the get methods. Inherits the rest of the fields from :class:`UserRoleRequest`
    """

    id = fields.Int()
    user = fields.Function(lambda obj: obj.user.username)
    role = fields.Function(lambda obj: obj.role.name)
