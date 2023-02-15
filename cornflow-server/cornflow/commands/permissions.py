from types import ModuleType
from typing import Union


def register_base_permissions_command(
    *, external_app: ModuleType = None, verbose: Union[bool, int] = False
):
    from flask import current_app
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from cornflow.endpoints import resources
    from cornflow_core.models import ViewBaseModel, PermissionViewRoleBaseModel
    from cornflow_core.shared import db
    from cornflow.shared.const import (
        BASE_PERMISSION_ASSIGNATION,
        EXTRA_PERMISSION_ASSIGNATION,
    )

    permissions_registered = [
        (perm.action_id, perm.api_view_id, perm.role_id)
        for perm in PermissionViewRoleBaseModel.get_all_objects()
    ]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on database commit: {e}")

    views = {view.name: view.id for view in ViewBaseModel.get_all_objects()}

    # Create base permissions
    permissions_to_register = [
        PermissionViewRoleBaseModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views[view["endpoint"]],
            }
        )
        for role, action in BASE_PERMISSION_ASSIGNATION
        for view in resources
        if role in view["resource"].ROLES_WITH_ACCESS
        and (
            action,
            views[view["endpoint"]],
            role,
        )
        not in permissions_registered
    ] + [
        PermissionViewRoleBaseModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views[endpoint],
            }
        )
        for role, action, endpoint in EXTRA_PERMISSION_ASSIGNATION
        if (
            action,
            views[endpoint],
            role,
        )
        not in permissions_registered
    ]

    if len(permissions_to_register) > 0:
        db.session.bulk_save_objects(permissions_to_register)

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

    if verbose == 1:
        if len(permissions_to_register) > 0:
            current_app.logger.info(
                f"Permissions registered: {permissions_to_register}"
            )
        else:
            current_app.logger.info("No new permissions to register")

    return True


def register_dag_permissions_command(open_deployment: int = None, verbose: int = 0):

    from flask import current_app
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from ..models import DeployedDAG, PermissionsDAG, UserModel
    from cornflow_core.shared import db

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

    all_users = UserModel.get_all_users()
    all_dags = DeployedDAG.get_all_objects()

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

    if verbose == 1:
        if len(permissions) > 1:
            current_app.logger.info(f"DAG permissions registered: {permissions}")
        else:
            current_app.logger.info("No new DAG permissions")

    pass
