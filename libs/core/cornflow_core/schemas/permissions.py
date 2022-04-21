"""
This file contains the schemas used for the endpoints that manage the permissions on views by roles
"""

# Imports from marshmallow library
from marshmallow import fields, Schema


class PermissionViewRoleBaseRequest(Schema):
    action_id = fields.Int()
    role_id = fields.Int()
    api_view_id = fields.Int()


class PermissionViewRoleBaseResponse(Schema):
    """
    Schema used for the get methods
    """

    id = fields.Int()
    action_id = fields.Int()
    action = fields.Function(lambda obj: obj.action.name.replace("_", " "))
    api_view_id = fields.Int()
    api_view = fields.Function(lambda obj: obj.api_view.name)
    role_id = fields.Int()
    role = fields.Function(lambda obj: obj.role.name)


class PermissionViewRoleBaseEditRequest(Schema):
    action_id = fields.Int(required=False)
    action = fields.Function(
        lambda obj: obj.action.name.replace("_", " "), required=False
    )
    api_view_id = fields.Int(required=False)
    api_view = fields.Function(lambda obj: obj.api_view.name, required=False)
    role_id = fields.Int(required=False)
    role = fields.Function(lambda obj: obj.role.name, required=False)
