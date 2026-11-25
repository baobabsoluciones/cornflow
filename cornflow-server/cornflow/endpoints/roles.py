"""
Endpoints to manage the roles of the application and the assignation fo roles to users.
Some of this endpoints are disable in case that the authentication is not performed over AUTH DB
"""
# Import from libraries
from flask import current_app
from flask_apispec import doc, marshal_with, use_kwargs

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import RoleModel
from cornflow.schemas.role import (
    RolesRequest,
    RolesResponse,
)
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.admin_access import is_reserved_role_id
from cornflow.shared.const import (
    AUTH_LDAP,
    NO_FREE_ROLE_ID_ERROR,
    PLATFORM_ADMIN_ROLE,
    RESERVED_ROLE_ERROR,
    RESERVED_ROLE_ID_ERROR,
    RESERVED_ROLE_RANGE,
)
from cornflow.shared.exceptions import (
    EndpointNotImplemented,
    InvalidUsage,
    NoPermission,
    ObjectAlreadyExists,
)

_RESERVED_LOW, _RESERVED_HIGH = RESERVED_ROLE_RANGE



def _deny_reserved_role(actor, role_id, action):
    """
    403 when an actor that is not a platform administrator touches a role in
    the reserved range (DA7).
    """
    if is_reserved_role_id(role_id) and not actor.is_platform_admin():
        raise NoPermission(
            error=RESERVED_ROLE_ERROR,
            log_txt=f"Error while user {actor} tries to {action} role {role_id}. "
            f"Role ids {_RESERVED_LOW}-{_RESERVED_HIGH} are reserved for the "
            f"platform roles.",
        )


class RolesListEndpoint(BaseMetaResource):
    # At security level 1 the client admin also reaches this endpoint
    # (LEVEL_PERMISSION_ASSIGNATION in shared/const.py); the reserved role range
    # stays with the platform administrator at every level.
    ROLES_WITH_ACCESS = [PLATFORM_ADMIN_ROLE]
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
        current_app.logger.info(f"User {self.get_user()} gets all the roles")
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
            err = "The roles have to be created in the directory."
            raise EndpointNotImplemented(
                err,
                log_txt=f"Error while user {self.get_user()} tries to create "
                        f"a new role through the endpoint. " + err
            )
        actor = self.get_user()
        role_id = kwargs.get("id")
        if role_id is not None:
            _deny_reserved_role(actor, role_id, "create")
            if is_reserved_role_id(role_id):
                raise InvalidUsage(
                    error=RESERVED_ROLE_ID_ERROR,
                    status_code=400,
                    log_txt=f"Error while user {actor} tries to create role "
                    f"{role_id}. " + RESERVED_ROLE_ID_ERROR,
                )
            if RoleModel.query.get(role_id) is not None:
                raise ObjectAlreadyExists(
                    log_txt=f"Error while user {actor} tries to create role "
                    f"{role_id}. The role already exists."
                )
        else:
            role_id = RoleModel.next_free_id_below_reserved_range()
            if role_id is None:
                raise InvalidUsage(
                    error=NO_FREE_ROLE_ID_ERROR,
                    status_code=400,
                    log_txt=f"Error while user {actor} tries to create a role. "
                    + NO_FREE_ROLE_ID_ERROR,
                )
            kwargs["id"] = role_id
        current_app.logger.info(f"User {actor} creates a new role")
        return self.post_list(kwargs)


class RoleDetailEndpoint(BaseMetaResource):
    # At security level 1 the client admin also reaches this endpoint
    # (LEVEL_PERMISSION_ASSIGNATION in shared/const.py); the reserved role range
    # stays with the platform administrator at every level.
    ROLES_WITH_ACCESS = [PLATFORM_ADMIN_ROLE]
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
        current_app.logger.info(f"User {self.get_user()} gets details of role {idx}")
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
            err = "The roles have to be modified in the directory."
            raise EndpointNotImplemented(
                err,
                log_txt=f"Error while user {self.get_user()} tries to edit "
                        f"a role through the endpoint. " + err
            )
        actor = self.get_user()
        _deny_reserved_role(actor, idx, "edit")
        if kwargs.get("id") is not None:
            _deny_reserved_role(actor, kwargs["id"], "move a role into")
        current_app.logger.info(f"User {actor} edits role {idx}")
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
        _deny_reserved_role(self.get_user(), idx, "delete")
        current_app.logger.error(f"User {self.get_user()} tries to delete role {idx}")
        err = "Roles can not be deleted"
        raise EndpointNotImplemented(
            err,
            log_txt=f"Error while user {self.get_user()} tries to delete a role. " + err
        )
