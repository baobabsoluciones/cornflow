"""

"""
# Import from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs
from flask_apispec.views import MethodResource

# Import from internal modules
from .meta_resource import MetaResource
from ..models import RoleModel
from ..schemas.roles import RolesRequest, RolesResponse
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, AUTH_LDAP, SERVICE_ROLE
from ..shared.exceptions import EndpointNotImplemented


class RolesListEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]
    DESCRIPTION = "Endpoint to get or create the current roles in the application"

    def __init__(self):
        super().__init__()
        self.model = RoleModel
        self.query = RoleModel.get_all_objects
        self.primary_key = "id"

    @doc(description="Gets all the roles", tags=["Roles"])
    @Auth.auth_required
    @marshal_with(RolesResponse(many=True))
    def get(self):
        """
        API method to get the roles defined in the application.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A dictionary with the response (data of the roles or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return RoleModel.get_all_objects()

    @doc(description="Creates a new role", tags=["Roles"])
    @Auth.auth_required
    @use_kwargs(RolesRequest, location="json")
    @marshal_with(RolesResponse)
    def post(self, **kwargs):
        """
        API method to create a new role for the application.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param dict kwargs: A dictionary with the needed data for the creation of a new role
        validated with schema :class:`RolesRequest`
        :return: A dictionary with the response (data of the new role or an error message)
        and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The roles have to be created in the active directory."
            )
        return self.post_list(kwargs)


class RoleDetailEndpoint(MetaResource, MethodResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE, SERVICE_ROLE]
    DESCRIPTION = "Endpoint to get, modify or delete a specific role of the application"

    def __init__(self):
        super().__init__()
        self.model = RoleModel
        self.query = RoleModel.get_one_object
        self.primary_key = "id"

    @doc(description="Gets one role", tags=["Roles"])
    @Auth.auth_required
    @marshal_with(RolesResponse)
    @MetaResource.get_data_or_404
    def get(self, idx):
        """
        API method to get one specific role of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the requested role
        :return: A dictionary with the response (data of the requested role or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return RoleModel.query.get(idx)

    @doc(description="Modifies one role", tags=["Roles"])
    @Auth.auth_required
    @use_kwargs(RolesResponse, location="json")
    def put(self, idx, **kwargs):
        """
        API method to modify an existing role of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the specific role
        :param dict kwargs: A dictionary with the needed data for the modification of a role
        validated with schema :class:`RolesResponse`
        :return: A dictionary with the response (a successful or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The roles have to be modified in the active directory."
            )
        return self.put_detail(kwargs, idx)

    @doc(description="Deletes one role", tags=["Roles"])
    @Auth.auth_required
    def delete(self, idx):
        """
        DEACTIVATED - NOT IMPLEMENTED

        API method to delete a role of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int idx: ID of the specific role
        :return: A dictionary with the response (a successful or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        raise EndpointNotImplemented(
            "The roles have to be deleted in the active directory."
        )
