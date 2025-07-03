import sys
from importlib import import_module

from flask import current_app

from cornflow.endpoints import alarms_resources, get_resources
from cornflow.models import RoleModel
from cornflow.shared.const import (
    EXTRA_PERMISSION_ASSIGNATION,
    ALL_DEFAULT_ROLES,
)
from cornflow.shared.const import ROLES_MAP


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

    # We extract the existing roles in the database
    existing_roles = [role.id for role in RoleModel.get_all_objects()]
    new_roles_to_add = []

    for role_id in roles_with_access:
        if role_id not in existing_roles:
            if role_id in ALL_DEFAULT_ROLES:
                # Create standard role with predefined name
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
