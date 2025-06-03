# Imports from external libraries
from flask import current_app
from importlib import import_module
from sqlalchemy.exc import DBAPIError, IntegrityError
import sys

# Imports from internal libraries
from cornflow.models import ViewModel
from cornflow.shared import db
from cornflow.endpoints import resources, alarms_resources


def register_views_command(external_app: str = None, verbose: bool = False):

    if external_app is None:
        resources_to_register = resources
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
    elif external_app is not None:
        sys.path.append("./")
        external_module = import_module(external_app)
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = (
                external_module.endpoints.resources + resources + alarms_resources
            )
        else:
            resources_to_register = external_module.endpoints.resources + resources
    else:
        resources_to_register = []
        exit()

    views_registered = [view.name for view in ViewModel.get_all_objects()]
    views_registered_urls_all_attributes = {
        view.name: {
            "url_rule": view.url_rule,
            "description": view.description,
            "id": view.id,
        }
        for view in ViewModel.get_all_objects()
    }
    views_to_register = [
        ViewModel(
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
        )
        for view in resources_to_register
        if view["endpoint"] not in views_registered
    ]

    all_resources_to_register_views_endpoints = {
        view["endpoint"]: {
            "url_rule": view["urls"],
            "description": view["resource"].DESCRIPTION,
        }
        for view in resources_to_register
    }

    # Check if views have the same name but different url_rule or description
    for view_name, view_attrs in views_registered_urls_all_attributes.items():
        if view_name in all_resources_to_register_views_endpoints.keys():
            new_endpoint = all_resources_to_register_views_endpoints[view_name]
            if (
                view_attrs["url_rule"] != new_endpoint["url_rule"]
                or view_attrs["description"] != new_endpoint["description"]
            ):
                # Update the object with new attributes
                ViewModel.update(
                    {
                        "id": view_attrs["id"],
                        "name": view_name,
                        "url_rule": new_endpoint["url_rule"],
                        "description": new_endpoint["description"],
                    },
                )
        else:
            ViewModel.delete(view_attrs["id"])

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
