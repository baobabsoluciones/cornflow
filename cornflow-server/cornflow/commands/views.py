import sys
from importlib import import_module

from cornflow_core.models import ViewBaseModel
from cornflow_core.shared import db
from flask import current_app
from sqlalchemy.exc import DBAPIError, IntegrityError


def register_views_command(external_app: str = None, verbose: bool = False):

    if external_app is None:
        from cornflow.endpoints import resources
    elif external_app is not None:
        sys.path.append("./")
        external_module = import_module(external_app)
        resources = external_module.endpoints.resources
    else:
        resources = []
        exit()

    views_registered = [view.name for view in ViewBaseModel.get_all_objects()]

    views_to_register = [
        ViewBaseModel(
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
        current_app.logger.error(f"Integrity error on views register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknow error on views register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('api_view', 'id'), MAX(id)) FROM api_view;"
        )
        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on views sequence updating: {e}")

    if verbose:
        if len(views_to_register) > 0:
            current_app.logger.info(f"Endpoints registered: {views_to_register}")
        else:
            current_app.logger.info("No new endpoints to be registered")

    return True
