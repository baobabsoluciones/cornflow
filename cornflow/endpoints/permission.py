"""

"""

# Import from libraries
from flask import current_app
from flask_apispec import marshal_with, use_kwargs, doc
from flask_apispec.views import MethodResource
import logging as log

# Import from internal modules
from .meta_resource import MetaResource
from ..models import PermissionViewRoleModel
from ..schemas.permission import (
    PermissionViewRoleResponse,
    PermissionViewRoleRequest,
    PermissionViewRoleEditRequest,
)
from ..shared.authentication import Auth
from ..shared.compress import compressed
from ..shared.const import ADMIN_ROLE, AUTH_LDAP
from ..shared.exceptions import EndpointNotImplemented, ObjectAlreadyExists


class PermissionsViewRoleEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = PermissionViewRoleModel
        self.query = PermissionViewRoleModel.get_all_objects
        self.primary_key = "id"

    @doc(
        description="Get all the permissions assigned to the roles",
        tags=["PermissionViewRole"],
    )
    @Auth.auth_required
    @marshal_with(PermissionViewRoleResponse(many=True))
    @compressed
    def get(self):
        """

        :return:
        :rtype:
        """
        return PermissionViewRoleModel.get_all_objects()

    @doc(description="Create a new permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    @use_kwargs(PermissionViewRoleRequest, location="json")
    @marshal_with(PermissionViewRoleResponse)
    def post(self, **kwargs):
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The permissions have to be created in the directory."
            )

        if PermissionViewRoleModel.get_permission(
            kwargs.get("role_id"), kwargs.get("api_view_id"), kwargs.get("action_id")
        ):
            raise ObjectAlreadyExists
        else:
            response = self.post_list(kwargs)
            log.info(
                "User {} creates permission {}".format(
                    self.get_user_id(), response[0].id
                )
            )
            return response


class PermissionsViewRoleDetailEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = PermissionViewRoleModel
        self.query = PermissionViewRoleModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Edit a permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    @use_kwargs(PermissionViewRoleEditRequest, location="json")
    def put(self, idx, **data):
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The permissions have to be modified in the directory."
            )
        response = self.put_detail(data, self.get_user(), idx)
        log.info("User {} edits permission {}".format(self.get_user_id(), idx))
        return response

    @doc(description="Delete a permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    def delete(self, idx):
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The permissions have to be deleted in the directory."
            )
        response = self.delete_detail(self.get_user(), idx)
        log.info("User {} deletes permission {}".format(self.get_user_id(), idx))
        return response
