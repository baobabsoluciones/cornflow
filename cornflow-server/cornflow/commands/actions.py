def register_actions_command(verbose: bool = True):
    from flask import current_app
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from cornflow_core.models import ActionBaseModel
    from cornflow.shared.const import ACTIONS_MAP
    from cornflow_core.shared import db

    actions_registered = [ac.name for ac in ActionBaseModel.get_all_objects()]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on database commit: {e}")

    actions_to_register = [
        ActionBaseModel(id=key, name=value)
        for key, value in ACTIONS_MAP.items()
        if value not in actions_registered
    ]
    print(f"Actions to register: {len(actions_to_register)}")

    if len(actions_to_register) > 0:
        db.session.bulk_save_objects(actions_to_register)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on actions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on actions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('actions', 'id'), MAX(id)) FROM actions;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on actions sequence updating: {e}")

    if verbose:
        if len(actions_to_register) > 0:
            current_app.logger.info("Actions registered: ", actions_to_register)
        else:
            current_app.logger.info("No new actions to be registered")

    return True
