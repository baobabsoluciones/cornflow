def register_base_permissions_command(verbose):
    from sqlalchemy.exc import IntegrityError

    from ..endpoints import resources
    from ..models import ApiViewModel, PermissionViewRoleModel
    from ..shared.const import BASE_PERMISSION_ASSIGNATION, EXTRA_PERMISSION_ASSIGNATION
    from ..shared.utils import db

    permissions_registered = [
        (perm.action_id, perm.api_view_id, perm.role_id)
        for perm in PermissionViewRoleModel.get_all_objects()
    ]

    db.session.commit()
    views = {view.name: view.id for view in ApiViewModel.get_all_objects()}

    # Create base permissions
    permissions_to_register = [
        PermissionViewRoleModel(
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
        PermissionViewRoleModel(
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
    except IntegrityError:
        db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_view', 'id'), MAX(id)) FROM permission_view;"
        )
        db.session.commit()

    if verbose == 1:
        if len(permissions_to_register) > 0:
            print("Permissions registered: ", permissions_to_register)
        else:
            print("No new permissions to register")

    return True


def register_base_dag_permissions_command(open_deployment: int = 1, verbose: int = 0):

    from sqlalchemy.exc import IntegrityError

    from ..models import DeployedDAG, PermissionsDAG, UserModel
    from ..shared.utils import db

    existing_permissions = [
        (permission.dag_id, permission.user_id)
        for permission in PermissionsDAG.get_all_objects()
    ]

    db.session.commit()
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
    except IntegrityError:
        db.session.rollback()

    if verbose == 1:
        if len(permissions) > 1:
            print(f"DAG permissions registered: {permissions}")
        else:
            print("No new DAG permissions")

    pass
