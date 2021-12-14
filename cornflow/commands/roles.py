def register_roles_command(verbose):
    from ..models import RoleModel
    from ..shared.const import ROLES_MAP
    from ..shared.utils import db

    roles_registered = [role.name for role in RoleModel.get_all_objects()]
    db.session.commit()

    roles_to_register = [
        RoleModel({"id": key, "name": value})
        for key, value in ROLES_MAP.items()
        if value not in roles_registered
    ]

    if len(roles_to_register) > 0:
        db.session.bulk_save_objects(roles_to_register)

    db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
        )
        db.session.commit()

    if verbose:
        if len(roles_to_register) > 0:
            print("Roles registered: ", roles_to_register)
        else:
            print("No new roles to be registered")

    return True
