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
    Schema used in the get and put methods. Inherits the resto of the fields from :class:`RolesRequest`
    """

    id = fields.Int()


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
    user = fields.Function(lambda obj: obj.user.name)
    role = fields.Function(lambda obj: obj.role.name)
