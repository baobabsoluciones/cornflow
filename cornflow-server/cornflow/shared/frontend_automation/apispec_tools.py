# Imports from external libraries
from flask import current_app
from flask_apispec.apidoc import ViewConverter, ResourceConverter
from flask_apispec.extension import FlaskApiSpec, make_apispec
from flask_apispec.paths import rule_to_path
from apispec import APISpec

# Imports from internal modules
from cornflow.models import (
    PermissionViewRoleModel,
    UserModel,
    ViewModel,
)
from .custom_marshmallow_plugin import (
    CustomMarshmallowPlugin,
)
from cornflow.shared.const import PERMISSION_METHOD_MAP


class CornflowUIApiSpec(FlaskApiSpec):
    """
    A subclass of FlaskApiSpec that avoids modifying the app's APISpec object,
    avoid errors when calling add_swagger_routes() on already initialized app,
    and handle user-specific documentation based on permissions.
    """

    def __init__(self, user_id, app=None, **kwargs):
        self.user_id = user_id
        super().__init__(app, **kwargs)

    def init_app(self, app):
        """
        Initialize the extension. Overwrites the init_app method of FlaskApiSpec to avoid errors
        when calling add_swagger_routes() on already initialized app. Also, creates a different
        APISpec object than the one in app.config to avoid modifying it.
        """
        self.app = app
        # Use custom APISpec with our CustomMarshmallowPlugin to include all metadata
        self.spec = APISpec(
            title="flask-apispec",
            version="v1",
            openapi_version="2.0",
            plugins=[CustomMarshmallowPlugin()],
        )
        self.resource_converter = LocalResourceConverter(
            self.user_id, self.app, self.spec, self.document_options
        )
        self.view_converter = ViewConverter(self.app, self.spec, self.document_options)

        for deferred in self._deferred:
            deferred()

    def _register(
        self,
        target,
        endpoint=None,
        blueprint=None,
        resource_class_args=None,
        resource_class_kwargs=None,
    ):
        """
        Register a resource or view function with the APISpec object.
        Overwrites the _register method of FlaskApiSpec to use allow for initialized resources
        as well as MetaResources.
        """
        from flask_apispec.views import MethodResource

        if isinstance(target, MethodResource):
            paths = self.resource_converter.convert(
                target,
                endpoint,
                blueprint,
                resource_class_args=resource_class_args,
                resource_class_kwargs=resource_class_kwargs,
            )
            for path in paths:
                self.spec.path(**path)
        else:
            super()._register(
                target,
                endpoint=None,
                blueprint=None,
                resource_class_args=None,
                resource_class_kwargs=None,
            )

    def get_registered(self, url_rule):
        """
        Get the registered methods for a given URL rule.
        :param url_rule: The URL rule of the endpoint.
        :return: A list of registered methods for the given URL rule.
        """
        return self.resource_converter.registered_methods.get(url_rule, [])


class LocalResourceConverter(ResourceConverter):
    """
    A subclass of ResourceConverter that overwrites get_operations to document only methods
    that have been decorated with @automate_frontend, and that the user has permission to access.
    """

    def __init__(self, user_id, *args, **kwargs):
        self.user_id = user_id
        self.registered_methods = {}
        super().__init__(*args, **kwargs)

    def get_operations(self, rule, resource):
        """
        Get the operations for a given resource and rule.
        Overwrites the get_operations method of ResourceConverter to document only methods
        that have been decorated with @automate_frontend, and that the user has permission to access.
        Also registers the methods that have been documented for each rule.
        :param rule: The URL rule of the endpoint.
        :param resource: The resource class of the endpoint.
        """
        operations = {
            method: getattr(resource, method.lower())
            for method in rule.methods
            if hasattr(resource, method.lower())
            and hasattr(getattr(resource, method.lower()), "__automate_frontend__")
            and self._user_has_permission(rule.rule, method)
        }
        self.registered_methods[rule.rule] = (
            rule_to_path(rule),
            list(operations.keys()),
        )
        return operations

    def _user_has_permission(self, url_rule, method):
        """
        Check if the user has permission to access the endpoint.
        :param url_rule: The URL rule of the endpoint.
        :param method: The method name (PUT, GET, POST, DELETE, PATCH).
        """
        user_roles = UserModel.get_one_user(self.user_id).roles
        action_id = PERMISSION_METHOD_MAP[method.upper()]
        try:
            view_id = ViewModel.query.filter_by(url_rule=url_rule).first().id
        except AttributeError:
            current_app.logger.error(f"View not found for URL {url_rule}")
            return False
        for role in user_roles:
            has_permission = PermissionViewRoleModel.get_permission(
                role_id=role, api_view_id=view_id, action_id=action_id
            )
            if has_permission:
                return True

        return False
