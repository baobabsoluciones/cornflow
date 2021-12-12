def register_views_command(verbose):
    from ..endpoints import resources
    from ..models import ApiViewModel
    from ..shared.utils import db

    views_registered = [view.name for view in ApiViewModel.get_all_objects()]

    db.session.commit()

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

    db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('api_view', 'id'), MAX(id)) FROM api_view;"
        )
        db.session.commit()

    if verbose == 1:
        if len(views_to_register) > 0:
            print("Endpoints registered: ", views_to_register)
        else:
            print("No new endpoints to be registered")

    return True
