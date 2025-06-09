def register_roles_command(external_app: str = None, verbose: bool = True):

    from sqlalchemy.exc import DBAPIError, IntegrityError
    from flask import current_app

    from cornflow.shared import db
    from cornflow.commands.auxiliar import (
        get_all_external,
        get_all_resources,
        get_new_roles_to_add,
    )

    resources_to_register, extra_permissions, _ = get_all_external(external_app)
    resources_roles_with_access = get_all_resources(resources_to_register)
    new_roles_to_add = get_new_roles_to_add(
        extra_permissions, resources_roles_with_access
    )

    if len(new_roles_to_add) > 0:
        db.session.bulk_save_objects(new_roles_to_add)

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
        if len(new_roles_to_add) > 0:
            current_app.logger.info(f"Roles registered: {new_roles_to_add}")
        else:
            current_app.logger.info("No new roles to be registered")

    return True
