# Imports from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.models import PermissionsDAG
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.exceptions import NoPermission
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.shared.const import VIEWER_ROLE
from cornflow.shared.frontend_automation.apispec_tools import CornflowUIApiSpec
from cornflow.schemas.frontend_automation import FrontendAutomationQuerySchema

# Imports from external libraries
from flask import current_app, g
from flask_apispec import doc, use_kwargs
from importlib import import_module
from importlib.metadata import entry_points
import os


class FrontendAutomationEndpoint(BaseMetaResource):
    """
    Endpoint for frontend automation.
    """

    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES
    DESCRIPTION = "Endpoint for frontend automation"

    @doc(
        description="Get the frontend automation information",
        tags=["Frontend Automation"],
    )
    @authenticate(auth_class=Auth())
    @use_kwargs(FrontendAutomationQuerySchema, location="query")
    def get(self, **kwargs):
        # Import here to avoid circular imports.
        # Get current app resources
        from . import resources as core_resources

        external_application = int(current_app.config["EXTERNAL_APP"])
        external_app_module = os.getenv("EXTERNAL_APP_MODULE")

        # Each entry is (resource_dict, output_url_prefix). The prefix is applied to the
        # URL shown to the client, never to the lookup key.
        url_prefix = "/cornflow/" if external_application == 1 else ""
        resources = [(res, url_prefix) for res in core_resources]

        # Get plugins resources
        for ep in entry_points(group="cornflow.plugins"):
            plugin = ep.load()()
            if hasattr(plugin, "get_resources"):
                resources += [(res, "") for res in plugin.get_resources()]

        # Get external app resources
        if external_application == 1:
            external_app_lib = import_module(external_app_module)
            try:
                external_app_resources = external_app_lib.endpoints.resources
                resources += [(res, "/external/") for res in external_app_resources]
            except AttributeError:
                current_app.logger.warning("No resources found in the external app")

        user_id = self.get_user_id()

        requested_schema = kwargs.get("schema", None)
        frontend_automations = {"tables": dict(), "groups": dict(), "sections": dict()}

        # Return an exception if the user specifically requested a schema they should
        #   not have access to.
        if requested_schema:
            has_permission = PermissionsDAG.check_if_has_permissions(
                user_id, requested_schema
            )
            if not has_permission:
                raise NoPermission(
                    error="You do not have permission to use this DAG",
                    status_code=403,
                    log_txt=f"Error while user {g.user} tries to access frontend_automation for "
                    f"dag {requested_schema}. The user does not have permission to "
                    f"access the dag.",
                )

        docs = CornflowUIApiSpec(user_id, current_app)
        # Maps the in-app (root) path apispec produces to the client-facing prefixed path,
        # so the "paths" block of the output is rewritten to match the URLs in
        # "available_automations".
        for resource, prefix in resources:
            endpoint_class = resource["resource"]()

            if endpoint_class.data_model is None:
                continue

            # If the user asked for a specific schema, we filter out the unrelated tables.
            #   We leave in the tables that are not related to a specific schema.
            frontend_table = getattr(
                endpoint_class.data_model, "__frontend_table__", None
            )
            if frontend_table:
                frontend_table = frontend_table()
            frontend_table_schemas = getattr(frontend_table, "schemas", None)
            if (
                requested_schema
                and frontend_table_schemas
                and requested_schema not in frontend_table_schemas
            ):
                continue

            # If the user did not ask for a specific schema, we filter out the tables they don't have
            #    access to based on their schemas.
            if frontend_table_schemas and not any(
                PermissionsDAG.check_if_has_permissions(user_id, schema)
                for schema in frontend_table_schemas
            ):
                continue

            apispec_info = {}
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if not hasattr(endpoint_class, method.lower()):
                    continue
                func = getattr(endpoint_class, method.lower())
                if not hasattr(func, "__automate_frontend__"):
                    continue

                apispec_info[method] = getattr(func, "__apispec__", None)
                func.__apispec__.update(func.__automate_frontend__["local_apispec"])

            docs.register(target=endpoint_class, endpoint=resource["endpoint"])

            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if method not in apispec_info:
                    continue
                func = getattr(endpoint_class, method.lower())
                func.__apispec__.update(apispec_info[method])

            # Document each method.
            output_url = (
                (prefix + resource["urls"]).replace("//", "/")
                if prefix
                else resource["urls"]
            )
            registered_output = docs.get_registered(output_url)
            if len(registered_output) == 0:
                # Try without the prefix, it's either one or the other. Plugins have
                #    the prefix in their registration, external apps don't.
                registered_output = docs.get_registered(resource["urls"])

            url, registered_operations = registered_output
            for func_name in registered_operations:
                method = getattr(endpoint_class, func_name.lower())
                frontend_automations = self._add_automation(
                    endpoint_class, method, output_url, frontend_automations
                )

        docs_spec = docs.spec.to_dict()

        # Remove empty paths (when no method is allowed to the user) and rewrite the
        # remaining keys to the client-facing prefixed URLs so "paths" matches the URLs
        # reported in "available_automations".
        new_paths = dict()
        for key, value in docs_spec["paths"].items():
            if len(value):
                new_paths[key] = value
        docs_spec["paths"] = new_paths

        # Add the info about the available tables and methods
        docs_spec["available_automations"] = frontend_automations

        return docs_spec, 200

    @staticmethod
    def _add_automation(endpoint_class, method, url, frontend_automations):
        """
        Add the automation information of a single method to the frontend_automations dictionary.
        """
        # Get table name
        table_name = endpoint_class.data_model.__tablename__

        # Initialize the table entry if not present
        frontend_table = getattr(endpoint_class.data_model, "__frontend_table__", None)
        frontend_group = getattr(frontend_table, "frontend_group", None)
        frontend_section = getattr(frontend_table, "frontend_section", None)
        if frontend_table:
            frontend_table = frontend_table()
        if frontend_group:
            frontend_group = frontend_group()
            frontend_section = getattr(frontend_group, "frontend_section", None)
        if frontend_section:
            frontend_section = frontend_section()
        frontend_automations["tables"][table_name] = frontend_automations["tables"].get(
            table_name,
            {
                "section": (
                    None
                    if frontend_group
                    else (frontend_section.name if frontend_section else None)
                ),
                "group": frontend_group.name if frontend_group else None,
                "title": getattr(frontend_table, "title", table_name),
                "icon": getattr(frontend_table, "icon", None),
                "schemas": getattr(frontend_table, "schemas", None),
                "model_table_name": getattr(
                    frontend_table, "model_table_name", table_name
                ),
                "order": getattr(frontend_table, "order", 0),
            },
        )

        # Add information about the group if there is one
        if frontend_group and frontend_group.name not in frontend_automations["groups"]:
            frontend_automations["groups"][frontend_group.name] = {
                "title": frontend_group.title,
                "icon": frontend_group.icon,
                "section": frontend_section.name if frontend_section else None,
                "order": frontend_group.order,
            }

        # Add information about the section if there is one
        if (
            frontend_section
            and frontend_section.name not in frontend_automations["sections"]
        ):
            frontend_automations["sections"][frontend_section.name] = {
                "title": frontend_section.title,
                "icon": frontend_section.icon,
                "order": frontend_section.order,
            }
        # Add information about the annotation
        endpoint_type = method.__automate_frontend__["endpoint_type"]
        # If the endpoint type is already present, log a warning and skip
        if endpoint_type in frontend_automations["tables"][table_name]:
            current_app.logger.warning(
                f"Duplicate frontend automation for {table_name} - {endpoint_type}."
                "Keeping the first one."
            )
            return frontend_automations
        # Add the annotation
        frontend_automations["tables"][table_name][endpoint_type] = {
            "url": url,
            "http_method": method.__name__.upper(),
        }
        return frontend_automations
