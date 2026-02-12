# Imports from external libraries
import sys
from importlib import import_module

from flask import current_app
from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow.endpoints import resources, alarms_resources

from cornflow.endpoints import alarms_resources, get_resources

# Imports from internal libraries
from cornflow.models import ViewModel
from cornflow.shared import db


def register_views_command(external_app: str = None, verbose: bool = False):
    """
    Register views for the application.
    external_app: If provided, it will register the views for the external app.
    verbose: If True, it will print the views that are being registered.
    """
    resources_to_register = get_resources_to_register(external_app)
    views_registered_urls_all_attributes = get_database_view()
    views_to_register, views_registered_urls_all_attributes = get_views_to_register(
        resources_to_register, views_registered_urls_all_attributes
    )
    views_to_delete, views_to_update = get_views_to_update_and_delete(
        resources_to_register, views_registered_urls_all_attributes
    )

    load_changes_to_db(views_to_delete, views_to_register, views_to_update)

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


def load_changes_to_db(views_to_delete, views_to_register, views_to_update):
    """
    Load changes to the database.
    views_to_delete: List of views to delete.
    views_to_register: List of views to register.
    views_to_update: List of views to update.
    """
    if len(views_to_register) > 0:
        db.session.bulk_save_objects(views_to_register)
    if len(views_to_update) > 0:
        db.session.bulk_update_mappings(ViewModel, views_to_update)
    # If the list views_to_delete is not empty, we will iterate over it and delete the views
    # If it is empty, we will not delete any view since we are iterating over an empty list
    for view_id in views_to_delete:
        view_to_delete = ViewModel.get_one_object(idx=view_id)
        if view_to_delete:
            view_to_delete.delete()
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on views register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknow error on views register: {e}")


def get_views_to_delete(
    all_resources_to_register_views_endpoints, views_registered_urls_all_attributes
):
    """
    Get the views to delete.
    Views to delete: exist in registered views but not in resources to register.
    """
    return [
        view_attrs["id"]
        for view_name, view_attrs in views_registered_urls_all_attributes.items()
        if view_name not in all_resources_to_register_views_endpoints
    ]


def get_views_to_update(
    all_resources_to_register_views_endpoints, views_registered_urls_all_attributes
):
    """
    Get the views to update.
    Views to update: exist in both but with different url_rule or description.
    """
    return [
        {
            "id": view_attrs["id"],
            "name": view_name,
            "url_rule": all_resources_to_register_views_endpoints[view_name][
                "url_rule"
            ],
            "description": all_resources_to_register_views_endpoints[view_name][
                "description"
            ],
        }
        for view_name, view_attrs in views_registered_urls_all_attributes.items()
        if view_name in all_resources_to_register_views_endpoints
        and (
            view_attrs["url_rule"]
            != all_resources_to_register_views_endpoints[view_name]["url_rule"]
            or view_attrs["description"]
            != all_resources_to_register_views_endpoints[view_name]["description"]
        )
    ]


def get_views_to_update_and_delete(
    resources_to_register, views_registered_urls_all_attributes
):
    """
    Get the views to update and delete.
    all_resources_to_register_views_endpoints: Dictionary of all resources to register views endpoints.
    views_registered_urls_all_attributes: Dictionary of views registered urls all attributes.
    """
    all_resources_to_register_views_endpoints = {
        view["endpoint"]: {
            "url_rule": view["urls"],
            "description": view["resource"].DESCRIPTION,
        }
        for view in resources_to_register
    }

    views_to_delete = get_views_to_delete(
        all_resources_to_register_views_endpoints, views_registered_urls_all_attributes
    )

    views_to_update = get_views_to_update(
        all_resources_to_register_views_endpoints, views_registered_urls_all_attributes
    )

    return views_to_delete, views_to_update


def get_views_to_register(resources_to_register, views_registered_urls_all_attributes):
    """
    Get the views to register.
    resources_to_register: List of resources to register.
    """

    views_to_register = [
        ViewModel(
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
        )
        for view in resources_to_register
        if view["endpoint"] not in views_registered_urls_all_attributes.keys()
    ]

    return views_to_register, views_registered_urls_all_attributes


def get_database_view():
    """
    Get the database views.
    """
    views_registered_urls_all_attributes = {
        view.name: {
            "url_rule": view.url_rule,
            "description": view.description,
            "id": view.id,
        }
        for view in ViewModel.get_all_objects()
    }
    return views_registered_urls_all_attributes


def get_resources_to_register(external_app):
    resources = get_resources()
    if external_app is None:
        resources_to_register = resources
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = resources + alarms_resources
            current_app.logger.info(" ALARMS ENDPOINTS ENABLED ")
    else:
        current_app.logger.info(f" USING EXTERNAL APP: {external_app} ")
        sys.path.append("./")
        external_module = import_module(external_app)
        if current_app.config["ALARMS_ENDPOINTS"]:
            resources_to_register = (
                external_module.endpoints.resources + resources + alarms_resources
            )
        else:
            resources_to_register = external_module.endpoints.resources + resources
    return resources_to_register
