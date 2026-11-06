import sys
from importlib import import_module

from flask import current_app

from cornflow.endpoints import alarms_resources, get_resources
from cornflow.models import RoleModel
from cornflow.shared.const import (
    EXTRA_PERMISSION_ASSIGNATION,
    ALL_DEFAULT_ROLES,
    RESERVED_ROLE_RANGE,
)
from cornflow.shared.const import ROLES_MAP
from cornflow.shared.exceptions import ConfigurationError


def get_all_external(external_app):
    """
    Get all resources, extra permissions, and custom roles actions.
    external_app: If provided, it will get the resources and extra permissions for the external app.
    """
    # We get base and conditional resources
    resources = get_resources()

    if external_app is None:
        resources_to_register = resources
        extra_permissions = EXTRA_PERMISSION_ASSIGNATION
        custom_roles_actions = {}
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
    else:
        sys.path.append("./")
        external_module = import_module(external_app)
        try:
            extra_permissions = (
                EXTRA_PERMISSION_ASSIGNATION
                + external_module.shared.const.EXTRA_PERMISSION_ASSIGNATION
            )
        except AttributeError:
            extra_permissions = EXTRA_PERMISSION_ASSIGNATION

        try:
            custom_roles_actions = external_module.shared.const.CUSTOM_ROLES_ACTIONS
        except AttributeError:
            custom_roles_actions = {}

        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = (
                external_module.endpoints.resources + resources + alarms_resources
            )
        else:
            resources_to_register = external_module.endpoints.resources + resources
    return resources_to_register, extra_permissions, custom_roles_actions


def get_all_resources(resources_to_register):
    """
    Get all resources and roles with access.
    resources_to_register: List of resources to register.
    """

    resources_roles_with_access = {
        resource["endpoint"]: resource["resource"].ROLES_WITH_ACCESS
        for resource in resources_to_register
    }

    return resources_roles_with_access


def check_reserved_role_ids(roles_with_access):
    """
    Guards the reserved role-id range (RESERVED_ROLE_RANGE, 900-999) that the
    cornflow platform roles live in.

    Refuses to register roles when:

    - a custom role (one not defined in ROLES_MAP) declares an id inside the
      reserved range, or
    - a role already stored in the database occupies a reserved id under a
      different name than the platform role that owns it.

    Both cases would silently reassign the meaning of existing role
    assignments (a deployment's custom role becoming a platform role), so the
    upgrade aborts with an explicit message instead.

    :param roles_with_access: the role ids referenced in code
    :raises ConfigurationError: on a collision
    """
    low, high = RESERVED_ROLE_RANGE

    trespassing = sorted(
        role_id
        for role_id in roles_with_access
        if low <= role_id <= high and role_id not in ROLES_MAP
    )
    if trespassing:
        # The lowest id available to a custom role: right above the core
        # client roles (the platform roles live in the reserved block, so they
        # must not be taken into account here)
        first_free = max(
            role for role in ALL_DEFAULT_ROLES if role < low
        ) + 1
        raise ConfigurationError(
            f"The role ids {trespassing} are inside the range "
            f"{low}-{high}, reserved for the cornflow platform roles. "
            f"Custom application roles must use ids between "
            f"{first_free} and {low - 1}."
        )

    for role in RoleModel.get_all_objects():
        if low <= role.id <= high and role.name != ROLES_MAP.get(role.id):
            raise ConfigurationError(
                f"The role id {role.id} is stored as '{role.name}' but it is "
                f"inside the range {low}-{high} reserved for the cornflow "
                f"platform roles (expected "
                f"'{ROLES_MAP.get(role.id, 'a platform role')}'). Renumber "
                f"that role — and its user assignments — outside the reserved "
                f"range before upgrading."
            )


def get_new_roles_to_add(extra_permissions, resources_roles_with_access):
    """
    Get the new roles to add.
    extra_permissions: List of extra permissions.
    resources_roles_with_access: Dictionary of resources and roles with access.
    """

    roles_with_access = list(
        set([role for roles in resources_roles_with_access.values() for role in roles])
    )
    roles_in_extra_permissions = [role for role, _, _ in extra_permissions]
    roles_with_access = list(set(roles_with_access + roles_in_extra_permissions))

    # Add all default roles that are referenced in BASE_PERMISSION_ASSIGNATION
    roles_with_access = list(set(roles_with_access + ALL_DEFAULT_ROLES))

    # Refuse to continue if a custom role trespasses on the reserved range or
    # a stored role already occupies a platform-role id
    check_reserved_role_ids(roles_with_access)

    # We extract the existing roles in the database
    existing_roles = [role.id for role in RoleModel.get_all_objects()]
    new_roles_to_add = []

    for role_id in roles_with_access:
        if role_id not in existing_roles:
            if role_id in ROLES_MAP:
                # Create role with its predefined name from ROLES_MAP
                role_name = ROLES_MAP[role_id]
                new_role = RoleModel(
                    {
                        "id": role_id,
                        "name": role_name,
                    }
                )
            else:
                # Create custom role with custom_role_<id> name
                new_role = RoleModel(
                    {
                        "id": role_id,
                        "name": f"custom_role_{role_id}",
                    }
                )
            new_roles_to_add.append(new_role)

    return new_roles_to_add
