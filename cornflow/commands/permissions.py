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
