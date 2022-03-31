def register_roles_command(verbose):
    import logging as log

    from sqlalchemy.exc import DBAPIError, IntegrityError

    from ..models import RoleModel
    from ..shared.const import ROLES_MAP
    from ..shared.utils import db

    roles_registered = [role.name for role in RoleModel.get_all_objects()]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on database commit: {e}")

    roles_to_register = [
        RoleModel({"id": key, "name": value})
        for key, value in ROLES_MAP.items()
        if value not in roles_registered
    ]

    if len(roles_to_register) > 0:
        db.session.bulk_save_objects(roles_to_register)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        log.error(f"Integrity error on roles register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on roles register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
        )
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on roles sequence updating: {e}")

    if verbose:
        if len(roles_to_register) > 0:
            print(f"Roles registered: {roles_to_register}")
        else:
            print("No new roles to be registered")

    return True