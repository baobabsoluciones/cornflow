def register_actions_command(verbose):
    import logging as log
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from ..models import ActionModel
    from ..shared.const import ACTIONS_MAP
    from cornflow_core.shared import database as db

    actions_registered = [ac.name for ac in ActionModel.get_all_objects()]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on database commit: {e}")

    actions_to_register = [
        ActionModel(id=key, name=value)
        for key, value in ACTIONS_MAP.items()
        if value not in actions_registered
    ]

    if len(actions_to_register) > 0:
        db.session.bulk_save_objects(actions_to_register)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        log.error(f"Integrity error on actions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on actions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('actions', 'id'), MAX(id)) FROM actions;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on actions sequence updating: {e}")

    if verbose == 1:
        if len(actions_to_register) > 0:
            print("Actions registered: ", actions_to_register)
        else:
            print("No new actions to be registered")

    return True
