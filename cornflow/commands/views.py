def register_views_command(verbose):
    import logging as log

    from sqlalchemy.exc import DBAPIError, IntegrityError

    from ..endpoints import resources
    from ..models import ApiViewModel
    from ..shared.utils import db

    views_registered = [view.name for view in ApiViewModel.get_all_objects()]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknown error on database commit: {e}")

    views_to_register = [
        ApiViewModel(
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
        )
        for view in resources
        if view["endpoint"] not in views_registered
    ]

    if len(views_to_register) > 0:
        db.session.bulk_save_objects(views_to_register)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        log.error(f"Integrity error on views register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        log.error(f"Unknow error on views register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('api_view', 'id'), MAX(id)) FROM api_view;"
        )
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on views sequence updating: {e}")

    if verbose == 1:
        if len(views_to_register) > 0:
            print(f"Endpoints registered: {views_to_register}")
        else:
            print("No new endpoints to be registered")

    return True
