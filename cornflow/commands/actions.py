def register_actions_command(verbose):
    from ..models import ActionModel
    from ..shared.const import ACTIONS_MAP
    from ..shared.utils import db

    actions_registered = [ac.name for ac in ActionModel.get_all_objects()]

    db.session.commit()

    actions_to_register = [
        ActionModel(id=key, name=value)
        for key, value in ACTIONS_MAP.items()
        if value not in actions_registered
    ]

    if len(actions_to_register) > 0:
        db.session.bulk_save_objects(actions_to_register)

    db.session.commit()

    # if "postgres" in str(db.session.get_bind()):
    #     db.engine.execute(
    #         "SELECT setval(pg_get_serial_sequence('actions', 'id'), MAX(id)) FROM actions;"
    #     )
    #     db.session.commit()

    if verbose == 1:
        if len(actions_to_register) > 0:
            print("Actions registered: ", actions_to_register)
        else:
            print("No new actions to be registered")

    return True
