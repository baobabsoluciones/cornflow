def register_roles_command(verbose: bool = True):

    from sqlalchemy.exc import DBAPIError, IntegrityError
    from flask import current_app

    from cornflow.models import RoleModel
    from cornflow.shared.const import ROLES_MAP
    from cornflow.shared import db

    roles_registered = [role.name for role in RoleModel.get_all_objects()]

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
        current_app.logger.error(f"Integrity error on roles register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on roles register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
        )
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on roles sequence updating: {e}")

    if verbose:
        if len(roles_to_register) > 0:
            current_app.logger.info(f"Roles registered: {roles_to_register}")
        else:
            current_app.logger.info("No new roles to be registered")

    return True
