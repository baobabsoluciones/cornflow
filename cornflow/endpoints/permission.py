"""

"""

# Import from libraries
from flask_apispec import doc, marshal_with, use_kwargs
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
from ..shared.const import ADMIN_ROLE
from ..shared.exceptions import ObjectAlreadyExists


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
        if PermissionViewRoleModel.get_permission(
            kwargs.get("role_id"), kwargs.get("api_view_id"), kwargs.get("action_id")
        ):
            raise ObjectAlreadyExists
        else:
            response = self.post_list(kwargs)
            log.info(
                f"User {self.get_user_id()} creates permission {response[0].id}"
            )
            return response


class PermissionsViewRoleDetailEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.model = PermissionViewRoleModel
        self.query = PermissionViewRoleModel.get_one_object
        self.primary_key = "id"

    @doc(description="Get one permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    @marshal_with(PermissionViewRoleResponse)
    @MetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get one specific permission of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the requested permission
        :return: A dictionary with the response (data of the requested permisssion or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return PermissionViewRoleModel.query.get(idx)

    @doc(description="Edit a permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    @use_kwargs(PermissionViewRoleEditRequest, location="json")
    def put(self, idx, **kwargs):
        response = self.put_detail(kwargs, idx)
        log.info(f"User {self.get_user_id()} edits permission {idx}")
        return response

    @doc(description="Delete a permission", tags=["PermissionViewRole"])
    @Auth.auth_required
    def delete(self, idx):
        response = self.delete_detail(idx)
        log.info(f"User {self.get_user_id()} deletes permission {idx}")
        return response
