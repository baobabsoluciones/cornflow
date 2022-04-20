"""
Endpoints to manage the roles of the application and the assignation fo roles to users.
Some of this endpoints are disable in case that the authentication is not performed over AUTH DB
"""

from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import EndpointNotImplemented
from cornflow_core.resources import BaseMetaResource

# Import from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from ..models import RoleModel
from cornflow_core.schemas import (
    RolesRequest,
    RolesResponse,
)
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, AUTH_LDAP


class RolesListEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = "Endpoint to get or create the current roles in the application"

    def __init__(self):
        super().__init__()
        self.data_model = RoleModel

    @doc(description="Gets all the roles", tags=["Roles"])
    @authenticate(auth_class=Auth())
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
        return self.get_list()

    @doc(description="Creates a new role", tags=["Roles"])
    @authenticate(auth_class=Auth())
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
                "The roles have to be created in the directory."
            )
        return self.post_list(kwargs)


class RoleDetailEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = "Endpoint to get, modify or delete a specific role of the application"

    def __init__(self):
        super().__init__()
        self.data_model = RoleModel

    @doc(description="Gets one role", tags=["Roles"])
    @authenticate(auth_class=Auth())
    @marshal_with(RolesResponse)
    @BaseMetaResource.get_data_or_404
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
        return self.get_detail(idx=idx)

    @doc(description="Modifies one role", tags=["Roles"])
    @authenticate(auth_class=Auth())
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
                "The roles have to be modified in the directory."
            )
        return self.put_detail(kwargs, idx=idx, track_user=False)

    @doc(description="Deletes one role", tags=["Roles"])
    @authenticate(auth_class=Auth())
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
        raise EndpointNotImplemented("Roles can not be deleted")
