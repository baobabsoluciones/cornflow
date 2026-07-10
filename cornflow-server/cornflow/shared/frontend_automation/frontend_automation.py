# Imports from external libraries
from enum import Enum
from flask import current_app
from flask_apispec.annotations import annotate
import functools
import pickle
from typing import Union

import logging
import marshmallow
import sys
import traceback


# Frontend automation constants
class EndpointTypes(Enum):
    """
    Types of API endpoints.
    """

    # Get all items. Accepts no parameters.
    #   Returns a list of items. Returns 200 if successful.
    GET_LIST = "get_list"
    # Get a single item by ID. Accepts item ID as parameter.
    #   Returns a single item. Returns 200 if successful.
    GET_ITEM = "get_item"
    # Create a new item. Accepts item data in request body, without an ID.
    #   Returns the created item. Returns 201 if successful.
    POST_ITEM = "post_item"
    # Update an existing item by ID. Accepts item ID as parameter and partial item data in request body.
    #   Returns only a message. Returns 200 if successful.
    PATCH_ITEM = "patch_item"
    # Replace an existing item by ID. Accepts item ID as parameter and full item data in request body.
    #   Returns the updated item. Returns 200 if successful.
    PUT_ITEM = "put_item"
    # Create multiple new items. Accepts a list of item data in request body, without IDs.
    #   Returns only a message. Returns 201 if successful. If there is an error, no items are created.
    POST_BULK = "post_bulk"
    # Update multiple existing items. Accepts a list of partial item data in request body, each with an ID.
    #   Returns only a message. Returns 200 if successful. If there is an error, no items are updated.
    POST_UPDATE_BULK = "post_update_bulk"
    # Delete an item by ID. Accepts item ID as parameter.
    #   Returns only a message. Returns 200 if successful.
    DELETE_ITEM = "delete_item"
    # Delete all items. Accepts no parameters.
    #   Returns only a message. Returns 200 if successful.
    DELETE_ALL = "delete_all"
    # Delete multiple items. Accepts a list of item IDs in request body: {"ids": [id1, id2, ...]}.
    #   Returns only a message. Returns 200 if successful. If there is an error, no items are deleted.
    DELETE_BULK = "delete_bulk"
    # Overwrite all items. Accepts a list of item data in request body, without IDs.
    #   Returns only a message. Returns 200 if successful. If there is an error, no items are created nor deleted.
    OVERWRITE_ALL = "overwrite_all"
    # Deletes all active items, and restore all previously deleted items. Accepts no parameters.
    #   Returns only a message. Returns 200 if successful. If there is an error, no items are deleted nor restored.
    RESTORE_ALL = "restore_all"
    # Download as an Excel. Accepts no parameters but can accept query arguments
    #   as filters, normally the same as the get_list endpoint except for limit and offset.
    #   Returns an Excel and status code 200 if successful.
    DOWNLOAD_EXCEL_TABLE = "download_excel_table"
    # Create multiple new items asynchronously by launching an airflow job.
    #   Accepts an unprocessed Excel.
    #   Returns an upload_id and a status string. Returns 202 if successful.
    ASYNC_POST_BULK = "async_post_bulk"
    # Update multiple existing items by launching an airflow job. Accepts an unprocessed Excel.
    #   Returns an upload_id and a status string. Returns 202 if successful.
    ASYNC_POST_UPDATE_BULK = "async_post_update_bulk"
    # Overwrite all items by launching an airflow job. Accepts an unprocessed Excel.
    #   Returns an upload_id and a status string. Returns 202 if successful.
    ASYNC_OVERWRITE_ALL = "async_overwrite_all"
    # Poll the status of an asynchronous upload. Accepts an upload_id in the url.
    #   Returns a json with a status string, a total_rows_loaded integer and eventually
    #   a `error_message` string.
    #   Returns 200 if successful.
    ASYNC_UPLOAD_STATUS = "async_upload_status"

    @property
    def needs_response_schema(self) -> bool:
        """
        Indicates if the endpoint type requires a response schema.
        """
        return self in [
            EndpointTypes.GET_LIST,
            EndpointTypes.GET_ITEM,
        ]

    @property
    def needs_request_schema(self) -> bool:
        """
        Indicates if the endpoint type requires a request schema.
        """
        return self in [
            EndpointTypes.POST_ITEM,
            EndpointTypes.PATCH_ITEM,
            EndpointTypes.PUT_ITEM,
            EndpointTypes.POST_BULK,
            EndpointTypes.POST_UPDATE_BULK,
            EndpointTypes.OVERWRITE_ALL,
            EndpointTypes.DELETE_BULK,
        ]


def automate_frontend(
    endpoint_type: EndpointTypes,
    schema_request: Union[marshmallow.Schema, marshmallow.schema.SchemaMeta] = None,
    schema_response: Union[marshmallow.Schema, marshmallow.schema.SchemaMeta] = None,
    schema_query: Union[marshmallow.Schema, marshmallow.schema.SchemaMeta] = None,
    overwrite_existing_annotations: bool = False,
):
    """
    Decorator to annotate API endpoint functions for frontend automation.
    If no request or response schema is provided, it will attempt to extract it from
    the function's api_spec annotations (if available). Therefore, this decorator
    should be applied after @marshal_with and @use_kwargs decorators (above them in the code).
    This decorator does not allow for the use of multiple @marshal_with or @use_kwargs,
    nor can it be applied several times to the same function.
    :param endpoint_type: Type of the endpoint (from EndpointTypes Enum)
    :param schema_request: Marshmallow schema for request validation
    :param schema_response: Marshmallow schema for response validation
    :param schema_query: Marshmallow schema for query parameters validation
    :param overwrite_existing_annotations: Whether to overwrite existing api_spec annotations if they exist.
        Defaults to True.
    """

    def decorator(func):
        """
        The actual decorator function.
        """
        # Using local logger because this decorator is called during app initialization,
        #   when flask app logger may not be fully configured yet.
        logger = _get_logger()
        if (
            hasattr(func, "__automate_frontend__")
            and not overwrite_existing_annotations
        ):
            logger.warning(
                f"Function {func.__qualname__} already has frontend automation annotations. Ignoring."
            )
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__apispec__ = {}

        try:
            schema_req = schema_request
            schema_res = schema_response

            # Validate endpoint_type
            if not isinstance(endpoint_type, EndpointTypes):
                logger.error(
                    f"Invalid endpoint_type {endpoint_type} for {func.__name__}. "
                    f"Must be an instance of EndpointTypes Enum."
                )
                return func

            # Check if there are existing @marshal_with annotations
            try:
                existing_res_schema = func.__apispec__["schemas"][0].options[0][
                    "default"
                ]["schema"]
            except (KeyError, IndexError, TypeError, AttributeError):
                existing_res_schema = None

            if schema_res is not None:
                # If a response schema is provided, write it into the api_spec
                #   If there also is an existing schema, log a warning and overwrite
                if existing_res_schema is not None:
                    logger.warning(
                        f"Function {func.__qualname__} already has @marshal_with annotations."
                        "Overwriting."
                    )
                options = {
                    "default": {
                        "schema": schema_res,
                    },
                }
                annotate(wrapper, "schemas", [options])
            elif existing_res_schema is None and endpoint_type.needs_response_schema:
                # If no response schema is provided nor found, and the endpoint needs it,
                #   log an error and do not add the annotation
                logger.warning(
                    f"Method {func.__qualname__} was provided with no response schema, and "
                    f"no response schema found in api_spec annotations. Ignoring."
                )
                return func

            # Check if there are existing @use_kwargs annotations
            try:
                existing_req_schemas_spec = [
                    annotation
                    for annotation in func.__apispec__["args"]
                    if annotation.options[0]["kwargs"]["location"] == "json"
                    or annotation.options[0]["kwargs"]["location"] is None
                ]
                existing_req_schema = existing_req_schemas_spec[0].options[0]["args"]
            except (KeyError, IndexError, TypeError, AttributeError):
                existing_req_schema = None

            if schema_req is not None:
                # If a request schema is provided, write it into the api_spec
                #   If there also is an existing schema, log a warning and overwrite
                if existing_req_schema:
                    logger.warning(
                        f"Function {func.__qualname__} already has @use_kwargs annotations."
                        "Overwriting."
                    )
                options = {
                    "args": schema_req,
                    "kwargs": {"location": "json"},
                }
                annotate(wrapper, "args", [options])
            elif existing_req_schema is None and endpoint_type.needs_request_schema:
                # If no request schema is provided nor found, and the endpoint needs it,
                #   log an error and do not add the annotation
                logger.warning(
                    f"Method {func.__qualname__} was provided with no request schema, and "
                    f"no request schema found in api_spec annotations. Ignoring."
                )
                return func

            # If a query schema is provided, write it into the api_spec
            try:
                existing_query_schemas_spec = [
                    annotation
                    for annotation in func.__apispec__["args"]
                    if annotation.options[0]["kwargs"]["location"] == "query"
                ]
                existing_query_schema = existing_query_schemas_spec[0].options[0][
                    "args"
                ]
            except (KeyError, IndexError, TypeError, AttributeError):
                existing_query_schema = None

            if schema_query is not None:
                if existing_query_schema:
                    logger.warning(
                        f"Function {func.__qualname__} already has query parameter annotations. Ignoring."
                    )
                options = {
                    "args": schema_query,
                    "kwargs": {"location": "query"},
                }
                annotate(wrapper, "args", [options])

            # Finally, add the frontend automation annotation
            wrapper.__automate_frontend__ = {
                "endpoint_type": endpoint_type.value,
                "local_apispec": wrapper.__apispec__,
            }

            # Copy existing api_spec annotations to the wrapper function
            wrapper.__apispec__ = pickle.loads(
                pickle.dumps(getattr(func, "__apispec__", {}).copy())
            )

        except TypeError:
            # We don't want to break the endpoint if something goes wrong
            logger.error(
                f"Error in automate_frontend for {func.__name__}: {traceback.format_exc()}."
                f"The automation annotation will not be added.",
            )
        return wrapper

    return decorator


def _get_logger():
    """
    Get local logger
    """
    if current_app:
        return current_app.logger

    logger = logging.getLogger("cornflow.automate_frontend")
    logger.setLevel(logging.INFO)

    # Add console handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
