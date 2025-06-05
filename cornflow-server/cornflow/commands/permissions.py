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
    if external_app is None:
        resources_to_register = resources
        extra_permissions = EXTRA_PERMISSION_ASSIGNATION
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
    elif external_app is not None:
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

    else:
        # Not reachable code
        resources_to_register = []
        exit()

    views_in_db = {view.name: view.id for view in ViewModel.get_all_objects()}
    permissions_in_db = [perm for perm in PermissionViewRoleModel.get_all_objects()]
    permissions_in_db_keys = [
        (perm.role_id, perm.action_id, perm.api_view_id) for perm in permissions_in_db
    ]
    resources_names = [resource["endpoint"] for resource in resources_to_register]
    resources_roles_with_access = {
        resource["endpoint"]: resource["resource"].ROLES_WITH_ACCESS
        for resource in resources_to_register
    }
    # We extract a unique list of roles with access
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

        # Create extended permission assignation including additional roles
        base_permissions_assignation = BASE_PERMISSION_ASSIGNATION + [
            (custom_role, action)
            for custom_role in additional_roles_with_access
            for action in ALL_DEFAULT_ACTIONS
        ]
    else:
        base_permissions_assignation = BASE_PERMISSION_ASSIGNATION

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

    # Convert set of tuples to list of PermissionViewRoleModel objects
    permissions_in_app = [
        PermissionViewRoleModel(
            {
                "role_id": role_id,
                "action_id": action_id,
                "api_view_id": api_view_id,
            }
        )
        for role_id, action_id, api_view_id in permissions_tuples
    ]

    permissions_in_app_keys = [
        (perm.role_id, perm.action_id, perm.api_view_id) for perm in permissions_in_app
    ]

    permissions_to_register = [
        permission
        for permission in permissions_in_app
        if (permission.role_id, permission.action_id, permission.api_view_id)
        not in permissions_in_db_keys
    ]

    permissions_to_delete = [
        permission
        for permission in permissions_in_db
        if (permission.role_id, permission.action_id, permission.api_view_id)
        not in permissions_in_app_keys
        and permission.api_view.name in resources_names
    ]

    # Save the new roles in the database
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

    # We check the roles have been correctly registered
    roles_in_db = [role.id for role in RoleModel.get_all_objects()]
    if len(new_roles_to_add) > 0:
        for role in new_roles_to_add:
            if role.id not in roles_in_db:
                current_app.logger.error(f"Role {role.id} not found in database")
    # We check the permissions have been correctly registered

    if len(permissions_to_register) > 0:
        roles_in_db = [role.id for role in PermissionViewRoleModel.get_all_objects()]

        # Check if any of the permissions to register already exist in the database
        permissions_in_db = [perm for perm in PermissionViewRoleModel.get_all_objects()]
        permissions_in_db_keys = [
            (perm.role_id, perm.action_id, perm.api_view_id)
            for perm in permissions_in_db
        ]

        # Filter out permissions that already exist in the database
        permissions_to_register = [
            permission
            for permission in permissions_to_register
            if (permission.role_id, permission.action_id, permission.api_view_id)
            not in permissions_in_db_keys
        ]
        # Get permissions that were filtered out because they already exist
        existing_permissions = [
            permission
            for permission in permissions_to_register
            if (permission.role_id, permission.action_id, permission.api_view_id)
            in permissions_in_db_keys
        ]

        if existing_permissions:
            for perm in existing_permissions:
                current_app.logger.info(
                    f"Permission already exists: role_id={perm.role_id}, action_id={perm.action_id}, api_view_id={perm.api_view_id}"
                )
        db.session.bulk_save_objects(permissions_to_register)

    # We are just going to register new permissions
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

    return True


def register_dag_permissions_command(
    open_deployment: int = None, verbose: bool = False
):

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
