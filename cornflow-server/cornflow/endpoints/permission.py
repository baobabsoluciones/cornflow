"""

"""

# Import from libraries
from flask_apispec import doc, marshal_with, use_kwargs
import logging as log
from cornflow_core.authentication import authenticate

# Import from internal modules
from ..models import PermissionViewRoleModel
from ..schemas.permission import (
    PermissionViewRoleResponse,
    PermissionViewRoleRequest,
    PermissionViewRoleEditRequest,
)
from ..shared.authentication import Auth
from ..shared.compress import compressed
from ..shared.const import ADMIN_ROLE
from cornflow_core.exceptions import ObjectAlreadyExists
from cornflow_core.resources import BaseMetaResource


class PermissionsViewRoleEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = PermissionViewRoleModel

    @doc(
        description="Get all the permissions assigned to the roles",
        tags=["PermissionViewRole"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(PermissionViewRoleResponse(many=True))
    @compressed
    def get(self):
        return self.get_list()

    @doc(description="Create a new permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @use_kwargs(PermissionViewRoleRequest, location="json")
    @marshal_with(PermissionViewRoleResponse)
    def post(self, **kwargs):
        if PermissionViewRoleModel.get_permission(
            role_id=kwargs.get("role_id"),
            api_view_id=kwargs.get("api_view_id"),
            action_id=kwargs.get("action_id"),
        ):
            raise ObjectAlreadyExists
        else:
            log.info(f"User {self.get_user_id()} creates permission")
            return self.post_list(kwargs)


class PermissionsViewRoleDetailEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = PermissionViewRoleModel

    @doc(description="Get one permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @marshal_with(PermissionViewRoleResponse)
    @BaseMetaResource.get_data_or_404
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
        return self.get_detail(idx=idx)

    @doc(description="Edit a permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @use_kwargs(PermissionViewRoleEditRequest, location="json")
    def put(self, idx, **kwargs):
        response = self.put_detail(kwargs, idx=idx, user=self.get_user())
        log.info(f"User {self.get_user_id()} edits permission {idx}")
        return response

    @doc(description="Delete a permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        response = self.delete_detail(idx=idx)
        log.info(f"User {self.get_user_id()} deletes permission {idx}")
        return response
