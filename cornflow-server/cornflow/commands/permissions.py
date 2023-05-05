import sys
from importlib import import_module

from cornflow.shared.const import (
    BASE_PERMISSION_ASSIGNATION,
    EXTRA_PERMISSION_ASSIGNATION,
)
from cornflow.models import ViewModel, PermissionViewRoleModel
from cornflow.shared import db
from flask import current_app
from sqlalchemy.exc import DBAPIError, IntegrityError


def register_base_permissions_command(external_app: str = None, verbose: bool = False):
    if external_app is None:
        from cornflow.endpoints import resources, alarms_resources
        resources_to_register = resources
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
    elif external_app is not None:
        sys.path.append("./")
        external_module = import_module(external_app)
        resources_to_register = external_module.endpoints.resources
    else:
        resources_to_register = []
        exit()

    views_in_db = {view.name: view.id for view in ViewModel.get_all_objects()}
    permissions_in_db = [perm for perm in PermissionViewRoleModel.get_all_objects()]
    permissions_in_db_keys = [
        (perm.role_id, perm.action_id, perm.api_view_id) for perm in permissions_in_db
    ]
    resources_names = [resource["endpoint"] for resource in resources_to_register]

    # Create base permissions
    permissions_in_app = [
        PermissionViewRoleModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views_in_db[view["endpoint"]],
            }
        )
        for role, action in BASE_PERMISSION_ASSIGNATION
        for view in resources_to_register
        if role in view["resource"].ROLES_WITH_ACCESS
    ] + [
        PermissionViewRoleModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views_in_db[endpoint],
            }
        )
        for role, action, endpoint in EXTRA_PERMISSION_ASSIGNATION
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

    if len(permissions_to_register) > 0:
        db.session.bulk_save_objects(permissions_to_register)

    # TODO: for now the permission are not going to get deleted just in case.
    #  We are just going to register new permissions
    # if len(permissions_to_delete) > 0:
    #     for permission in permissions_to_delete:
    #         db.session.delete(permission)

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
