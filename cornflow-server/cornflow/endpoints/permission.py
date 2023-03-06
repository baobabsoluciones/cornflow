"""

"""

# Import from internal modules
from cornflow_core.authentication import authenticate
from cornflow_core.compress import compressed
from cornflow_core.exceptions import ObjectAlreadyExists
from cornflow_core.models import PermissionViewRoleBaseModel
from cornflow_core.resources import BaseMetaResource
from cornflow_core.schemas import (
    PermissionViewRoleBaseEditRequest,
    PermissionViewRoleBaseRequest,
    PermissionViewRoleBaseResponse,
)

# Import from libraries
from flask_apispec import doc, marshal_with, use_kwargs
from flask import current_app

from cornflow.shared.authentication import Auth
from cornflow.shared.const import ADMIN_ROLE


class PermissionsViewRoleEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = PermissionViewRoleBaseModel

    @doc(
        description="Get all the permissions assigned to the roles",
        tags=["PermissionViewRole"],
    )
    @authenticate(auth_class=Auth())
    @marshal_with(PermissionViewRoleBaseResponse(many=True))
    @compressed
    def get(self):
        current_app.logger.info(
            f"User {self.get_user()} gets all permissions assigned to the roles"
        )
        return self.get_list()

    @doc(description="Create a new permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @use_kwargs(PermissionViewRoleBaseRequest, location="json")
    @marshal_with(PermissionViewRoleBaseResponse)
    def post(self, **kwargs):
        if PermissionViewRoleBaseModel.get_permission(
            role_id=kwargs.get("role_id"),
            api_view_id=kwargs.get("api_view_id"),
            action_id=kwargs.get("action_id"),
        ):
            raise ObjectAlreadyExists(
                log_txt=f"Error while user {self.get_user()} tries to create a new permission. "
                f"The permission already exists."
            )
        else:
            current_app.logger.info(f"User {self.get_user()} creates permission")
            return self.post_list(kwargs)


class PermissionsViewRoleDetailEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = PermissionViewRoleBaseModel

    @doc(description="Get one permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @marshal_with(PermissionViewRoleBaseResponse)
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
        current_app.logger.info(
            f"User {self.get_user()} gets details of permission {idx}"
        )
        return self.get_detail(idx=idx)

    @doc(description="Edit a permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    @use_kwargs(PermissionViewRoleBaseEditRequest, location="json")
    def put(self, idx, **kwargs):
        response = self.put_detail(kwargs, idx=idx, track_user=False)
        current_app.logger.info(f"User {self.get_user()} edits permission {idx}")
        return response

    @doc(description="Delete a permission", tags=["PermissionViewRole"])
    @authenticate(auth_class=Auth())
    def delete(self, idx):
        response = self.delete_detail(idx=idx)
        current_app.logger.info(f"User {self.get_user()} deletes permission {idx}")
        return response
