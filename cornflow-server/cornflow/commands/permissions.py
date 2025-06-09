import sys
from importlib import import_module

from cornflow.shared.const import (
    BASE_PERMISSION_ASSIGNATION,
    EXTRA_PERMISSION_ASSIGNATION,
    ALL_DEFAULT_ACTIONS,
    ALL_DEFAULT_ROLES,
)
from cornflow.models import ViewModel, PermissionViewRoleModel, RoleModel
from cornflow.shared import db

from flask import current_app
from sqlalchemy.exc import DBAPIError, IntegrityError
from cornflow.endpoints import resources, alarms_resources


def register_base_permissions_command(external_app: str = None, verbose: bool = False):
    """
    Register base permissions for the application.
    external_app: If provided, it will register the permissions for the external app.
    verbose: If True, it will print the permissions that are being registered.
    """
    # Get all resources and extra permissions
    resources_to_register, extra_permissions = get_all_external(external_app)
    # Get all views in the database
    views_in_db = {view.name: view.id for view in ViewModel.get_all_objects()}
    permissions_in_db, permissions_in_db_keys = get_db_permissions()
    # Get all resources and roles with access
    resources_roles_with_access = get_all_resources(resources_to_register)
    new_roles_to_add = get_new_roles_to_add(
        extra_permissions, resources_roles_with_access
    )
    # Get the new roles and base permissions assignation
    base_permissions_assignation = get_base_permissions(
        new_roles_to_add, resources_roles_with_access
    )
    # Get the permissions to register and delete
    permissions_tuples = get_permissions_in_code_as_tuples(
        resources_to_register,
        views_in_db,
        base_permissions_assignation,
        extra_permissions,
    )
    permissions_to_register = get_permissions_to_register(
        permissions_tuples, permissions_in_db_keys
    )
    permissions_to_delete = get_permissions_to_delete(
        permissions_tuples, resources_roles_with_access.keys(), permissions_in_db
    )

    # Save the new roles in the database
    save_new_roles(new_roles_to_add)
    save_and_delete_permissions(permissions_to_register, permissions_to_delete)

    if verbose:
        if len(permissions_to_register) > 0:
            current_app.logger.info(
                f"Permissions registered: {permissions_to_register}"
            )
        else:
            current_app.logger.info("No new permissions to register")

        if len(permissions_to_delete) > 0:
            current_app.logger.info(f"Permissions deleted: {permissions_to_delete}")
        else:
            current_app.logger.info("No permissions to delete")


def save_new_roles(new_roles_to_add):
    """
    Save the new roles in the database.
    new_roles_to_add: List of new roles to add.
    """
    if len(new_roles_to_add) > 0:
        db.session.bulk_save_objects(new_roles_to_add)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Integrity error on base permissions register: {e}"
            )
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on base permissions register: {e}")


def save_and_delete_permissions(permissions_to_register, permissions_to_delete):
    """
    Save and delete permissions in the database.
    permissions_to_register: List of permissions to register.
    permissions_to_delete: List of permissions to delete.
    """
    if len(permissions_to_register) > 0:
        db.session.bulk_save_objects(permissions_to_register)

    if len(permissions_to_delete) > 0:
        for permission in permissions_to_delete:
            db.session.delete(permission)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on base permissions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on base permissions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_view', 'id'), MAX(id)) FROM permission_view;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unknown error on base permissions sequence updating: {e}"
            )


def get_permissions_to_delete(permissions_tuples, resources_names, permissions_in_db):
    """
    Get the permissions to delete.
    """
    permissions_to_delete = [
        permission
        for permission in permissions_in_db
        if (permission.role_id, permission.action_id, permission.api_view_id)
        not in permissions_tuples
    ]

    return permissions_to_delete


def get_permissions_to_register(permissions_tuples, permissions_in_db_keys):
    """
    Get the permissions to register.
    """
    # Convert set of tuples to list of PermissionViewRoleModel objects
    return [
        PermissionViewRoleModel(
            {
                "role_id": role_id,
                "action_id": action_id,
                "api_view_id": api_view_id,
            }
        )
        for role_id, action_id, api_view_id in permissions_tuples
        if (role_id, action_id, api_view_id) not in permissions_in_db_keys
    ]


def get_permissions_in_code_as_tuples(
    resources_to_register, views_in_db, base_permissions_assignation, extra_permissions
):
    """
    Get the permissions in code as tuples.
    """
    # Create base permissions using a set to avoid duplicates
    permissions_tuples = set()

    # Add permissions from ROLES_WITH_ACCESS
    for role, action in base_permissions_assignation:
        for view in resources_to_register:
            if role in view["resource"].ROLES_WITH_ACCESS:
                permissions_tuples.add((role, action, views_in_db[view["endpoint"]]))

    # Add permissions from extra_permissions
    for role, action, endpoint in extra_permissions:
        if endpoint in views_in_db:
            permissions_tuples.add((role, action, views_in_db[endpoint]))

    return permissions_tuples


def get_base_permissions(new_roles_to_add, resources_roles_with_access):
    """
    Get the new roles and base permissions assignation.
    new_roles_to_add: List of new roles to add.
    resources_roles_with_access: Dictionary of resources and roles with access.
    """
    # Get all custom roles (both new and existing) that appear in ROLES_WITH_ACCESS
    all_custom_roles_in_access = set(
        [
            role
            for roles in resources_roles_with_access.values()
            for role in roles
            if role not in ALL_DEFAULT_ROLES
        ]
    )

    # Create extended permission assignation including all custom roles
    base_permissions_assignation = BASE_PERMISSION_ASSIGNATION + [
        (custom_role, action)
        for custom_role in all_custom_roles_in_access
        for action in ALL_DEFAULT_ACTIONS
    ]

    return base_permissions_assignation


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
    # We check if there is any role additional to the ones defined in the base permissions
    additional_roles_with_access = [
        role for role in roles_with_access if role not in ALL_DEFAULT_ROLES
    ]

    # We extract the existing roles in the database
    existing_roles = [role.id for role in RoleModel.get_all_objects()]
    new_roles_to_add = []
    if len(additional_roles_with_access) > 0:
        # If our id is not in the existing roles, we add it, applying a
        # pre-defined name custom_role_<id>
        for custom_role in additional_roles_with_access:
            if custom_role not in existing_roles:
                new_role = RoleModel(
                    {
                        "id": custom_role,
                        "name": f"custom_role_{custom_role}",
                    }
                )
                new_roles_to_add.append(new_role)
    return new_roles_to_add


def get_all_external(external_app):
    """
    Get all resources and extra permissions.
    external_app: If provided, it will get the resources and extra permissions for the external app.
    """
    if external_app is None:
        resources_to_register = resources
        extra_permissions = EXTRA_PERMISSION_ASSIGNATION
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

        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = (
                external_module.endpoints.resources + resources + alarms_resources
            )
        else:
            resources_to_register = external_module.endpoints.resources + resources
    return resources_to_register, extra_permissions


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


def get_db_permissions():
    """
    Get all permissions in the database.
    """
    permissions_in_db = [perm for perm in PermissionViewRoleModel.get_all_objects()]
    permissions_in_db_keys = [
        (perm.role_id, perm.action_id, perm.api_view_id) for perm in permissions_in_db
    ]

    return permissions_in_db, permissions_in_db_keys


def register_dag_permissions_command(
    open_deployment: int = None, verbose: bool = False
):
    """
    Register DAG permissions.
    open_deployment: If 1, it will register the permissions for the open deployment.
    verbose: If True, it will print the permissions that are being registered.
    """

    from flask import current_app
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from cornflow.models import DeployedDAG, PermissionsDAG, UserModel
    from cornflow.shared import db

    if open_deployment is None:
        open_deployment = int(current_app.config["OPEN_DEPLOYMENT"])

    existing_permissions = [
        (permission.dag_id, permission.user_id)
        for permission in PermissionsDAG.get_all_objects()
    ]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on database commit: {e}")

    all_users = UserModel.get_all_users().all()
    all_dags = DeployedDAG.get_all_objects().all()

    if open_deployment == 1:
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user.id})
            for user in all_users
            for dag in all_dags
            if (dag.id, user.id) not in existing_permissions
        ]

    else:
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user.id})
            for user in all_users
            for dag in all_dags
            if (dag.id, user.id) not in existing_permissions and user.is_service_user()
        ]

    if len(permissions) > 1:
        db.session.bulk_save_objects(permissions)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on dag permissions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on dag permissions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_dag', 'id'), MAX(id)) FROM permission_dag;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unknown error on dag permissions sequence updating: {e}"
            )

    if verbose:
        if len(permissions) > 1:
            current_app.logger.info(f"DAG permissions registered: {permissions}")
        else:
            current_app.logger.info("No new DAG permissions")

    pass
