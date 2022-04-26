"""
Endpoints to manage the roles of the application and the assignation fo roles to users.
Some of this endpoints are disable in case that the authentication is not performed over AUTH DB
"""

from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import EndpointNotImplemented, ObjectAlreadyExists
from cornflow_core.resources import BaseMetaResource

# Import from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from ..models import UserRoleModel
from cornflow_core.schemas import (
    UserRoleRequest,
    UserRoleResponse,
)
from ..shared.authentication import Auth
from ..shared.const import ADMIN_ROLE, AUTH_LDAP


class UserRoleListEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = (
        "Endpoint to get the list of roles assigned to users and create new assignments"
    )

    def __init__(self):
        super().__init__()
        self.data_model = UserRoleModel

    @doc(description="Gets all the user role assignments", tags=["User roles"])
    @authenticate(auth_class=Auth())
    @marshal_with(UserRoleResponse(many=True))
    def get(self):
        """
        API method to get the assigned roles to the users defined in the application.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :return: A dictionary with the response (data of the user assigned roles or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)

        """
        return self.get_list()

    @doc(description="Creates a new role assignment", tags=["User roles"])
    @authenticate(auth_class=Auth())
    @use_kwargs(UserRoleRequest)
    @marshal_with(UserRoleResponse)
    def post(self, **kwargs):
        """

        API method to create a new role assignation for a user for the application.
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param dict kwargs: A dictionary with the needed data for the creation of the new role assignation
        validated with schema :class:`UserRoleRequest`
        :return: A dictionary with the response (data of the new role or an error message)
        and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The role assignments have to be created in the directory"
            )

        # Check if the assignation is disabled, or it does exist
        if UserRoleModel.check_if_role_assigned_disabled(**kwargs):
            return self.activate_detail(**kwargs)
        elif UserRoleModel.check_if_role_assigned(**kwargs):
            raise ObjectAlreadyExists()
        else:
            # Admin id so it does not override user_id that appear on the table based on the user that makes
            # the request that doesn't have to be the user that is getting a role
            return self.post_list(kwargs, trace_field="admin_id")


class UserRoleDetailEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [ADMIN_ROLE]
    DESCRIPTION = "Endpoint to get a specific role assignment or to delete one"

    def __init__(self):
        super().__init__()
        self.data_model = UserRoleModel

    @doc(description="Gets one user role assignment", tags=["User roles"])
    @authenticate(auth_class=Auth())
    @marshal_with(UserRoleResponse)
    def get(self, user_id, role_id):
        """
        API method to get one specific role assignation of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int user_id: ID of the requested user
        :param int role_id: ID of the requested role
        :return: A dictionary with the response (data of the requested role assignation or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        return self.get_detail(user_id=user_id, role_id=role_id)

    @doc(description="Deletes one user role assignment", tags=["User roles"])
    @authenticate(auth_class=Auth())
    def delete(self, user_id, role_id):
        """
        API method to delete a role assignation of the application
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user.

        :param int user_id: ID of the requested user
        :param int role_id: ID of the requested role
        :return: A dictionary with the response (a successful or an error message)
        and an integer with the HTTP status code.
        :rtype: Tuple(dict, integer)
        """
        # TODO: maybe we should check if the user "is LDAP" [user_obj.comes_from_ldap()]
        #  like in UserDetailsEndpoint.put
        AUTH_TYPE = current_app.config["AUTH_TYPE"]
        if AUTH_TYPE == AUTH_LDAP:
            raise EndpointNotImplemented(
                "The roles have to be created in the directory."
            )
        return self.delete_detail(user_id=user_id, role_id=role_id)