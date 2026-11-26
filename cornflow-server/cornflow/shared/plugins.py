"""
Support for the applications that extend cornflow as plugins.

In plugin mode (``EXTERNAL_APP=0``) ``create_app`` loads every object published
under the ``cornflow.plugins`` entry point group and calls its ``init_app``.
The resources each plugin mounts are recorded on the application, so the
access initialization keeps the plugin views instead of deleting them as
obsolete, asks each plugin to register its own roles, views and permissions,
and then leaves the permissions on the views of the plugin exactly as its
code declares them.
"""

import importlib.metadata

from cornflow.shared.const import CORNFLOW_BLUEPRINT_NAME, LEGACY_ENDPOINT_SUFFIX

PLUGIN_ENTRY_POINT_GROUP = "cornflow.plugins"
PLUGINS_EXTENSION = "cornflow_plugins"
CORE_OWNER = "cornflow"
# Methods that Flask adds to every rule: they do not make two rules clash
_AUTOMATIC_METHODS = {"HEAD", "OPTIONS"}


class PluginLoadError(RuntimeError):
    """A plugin could not be loaded or clashes with cornflow or another plugin."""


class CornflowPlugin:
    """
    Base class for the cornflow plugins.

    ``init_app`` runs in the order the entry points are discovered, not by
    ``priority``. A plugin that fails to load, or that mounts an endpoint name
    or a URL already used by cornflow or by another plugin, stops cornflow
    from starting with an error that names the plugin.

    :cvar int priority: order in which the plugins register their access,
      lower values first. Plugins with the same priority keep the discovery order.
    """

    priority = 0

    def init_app(self, app) -> None:
        """
        Mounts the plugin on the cornflow application (routes, configuration...).

        :param app: the cornflow Flask application
        """
        raise NotImplementedError

    def register_access(self, app) -> None:
        """
        Registers the roles, views and permissions the plugin needs.

        Cornflow calls it on every access initialization (``access_init``,
        ``cornflow service init``) right after registering its own access, so
        it must be idempotent. Right after it, cornflow leaves the permissions
        on the views mounted by the plugin exactly as the code declares them
        (the ``ROLES_WITH_ACCESS`` of each resource and the actions given by
        :meth:`get_custom_roles_actions`): the missing ones are created and the
        ones not declared, including those added by hand, are deleted.

        The default implementation does nothing, but cornflow still leaves the
        permissions on the views of the plugin as its code declares them, as
        described above. Only an object that does not have a
        ``register_access`` method (one that does not subclass this class)
        is left out: cornflow does not touch the permissions on its views.

        :param app: the cornflow Flask application
        """
        return None

    def get_custom_roles_actions(self) -> dict:
        """
        Returns the actions allowed to the plugin's own roles, with the same
        shape as ``CUSTOM_ROLES_ACTIONS``: ``{role_id: [action_id, ...]}``.
        Every role in a ``ROLES_WITH_ACCESS`` of the plugin that is not a
        cornflow role has to be defined here.

        :return: the actions of the custom roles, none by default
        """
        return {}


class LoadedPlugin:
    """
    A plugin mounted on the application, together with the resources it added.

    :param str name: the entry point name
    :param plugin: the plugin object
    :param list resources: the resources mounted by the plugin, with the same
      shape as the cornflow resources (``endpoint``, ``urls`` and ``resource``)
    """

    def __init__(self, name, plugin, resources):
        self.name = name
        self.plugin = plugin
        self.resources = resources

    @property
    def priority(self):
        return getattr(self.plugin, "priority", 0)


def _mounted_resources(app, view_functions_before):
    """
    Returns the resources mounted since the snapshot of the view functions
    was taken: the new endpoints and the ones whose view was replaced. Only
    the API resources (views with a ``DESCRIPTION``) are returned, as they are
    the ones that need a view in the permission system.
    """
    resources = []
    for endpoint, view_function in app.view_functions.items():
        if view_functions_before.get(endpoint) is view_function:
            continue
        resource = getattr(view_function, "view_class", None)
        if resource is None or not hasattr(resource, "DESCRIPTION"):
            continue
        try:
            rules = list(app.url_map.iter_rules(endpoint))
        except KeyError:
            rules = []
        if not rules:
            continue
        resources.append(
            {"endpoint": endpoint, "urls": rules[0].rule, "resource": resource}
        )
    return resources


def _view_name(endpoint):
    """
    Name of the view behind an endpoint in the permission system: the core
    endpoints are mounted as ``cornflow.<name>`` and as the alias
    ``<name>_compat``.
    """
    prefix = f"{CORNFLOW_BLUEPRINT_NAME}."
    if endpoint.startswith(prefix):
        return endpoint[len(prefix):]
    if endpoint.endswith(LEGACY_ENDPOINT_SUFFIX):
        return endpoint[: -len(LEGACY_ENDPOINT_SUFFIX)]
    return endpoint


def _rules_clash(rule, other):
    """Whether two URL rules serve the same path for a common method."""
    if rule.rule != other.rule:
        return False
    if rule.methods is None or other.methods is None:
        return True
    return bool((rule.methods & other.methods) - _AUTOMATIC_METHODS)


def _check_collisions(app, plugin_name, view_functions_before, rules_before, owners):
    """
    Raises :class:`PluginLoadError` if the plugin just mounted replaced an
    existing endpoint, used the name of an existing one (also of a core
    endpoint, mounted as ``cornflow.<name>``) or mounted a URL already served
    for the same method.

    :param app: the cornflow Flask application
    :param str plugin_name: the entry point name of the plugin
    :param dict view_functions_before: the view functions before the plugin
    :param list rules_before: the URL rules before the plugin
    :param dict owners: who mounted each previous endpoint (cornflow or a plugin)
    """
    names_before = {_view_name(endpoint): endpoint for endpoint in view_functions_before}
    for endpoint, view_function in app.view_functions.items():
        previous = view_functions_before.get(endpoint)
        if previous is view_function:
            continue
        if previous is not None:
            raise PluginLoadError(
                f"The plugin {plugin_name} replaces the endpoint {endpoint} of "
                f"{owners.get(endpoint, CORE_OWNER)}"
            )
        clash = names_before.get(_view_name(endpoint))
        if clash is not None:
            raise PluginLoadError(
                f"The plugin {plugin_name} mounts the endpoint {endpoint}, with the "
                f"name of the endpoint {clash} of {owners.get(clash, CORE_OWNER)}"
            )
        try:
            rules = list(app.url_map.iter_rules(endpoint))
        except KeyError:
            rules = []
        for rule in rules:
            for other in rules_before:
                if _rules_clash(rule, other):
                    raise PluginLoadError(
                        f"The plugin {plugin_name} mounts the URL {rule.rule} "
                        f"(endpoint {endpoint}), already served by the endpoint "
                        f"{other.endpoint} of {owners.get(other.endpoint, CORE_OWNER)}"
                    )


def load_plugins(app):
    """
    Loads and mounts the plugins published under the ``cornflow.plugins``
    entry point group, recording the resources each one mounts.

    A plugin that fails to load or to mount, or that mounts an endpoint name
    or a URL already in use (by cornflow or by a plugin loaded before),
    raises :class:`PluginLoadError` naming the plugin, so cornflow does not
    start.

    :param app: the cornflow Flask application
    """
    loaded = []
    owners = {endpoint: CORE_OWNER for endpoint in app.view_functions}
    for entry_point in importlib.metadata.entry_points(group=PLUGIN_ENTRY_POINT_GROUP):
        view_functions_before = dict(app.view_functions)
        rules_before = list(app.url_map.iter_rules())
        try:
            plugin = entry_point.load()()
            plugin.init_app(app)
        except Exception as error:
            raise PluginLoadError(
                f"The plugin {entry_point.name} failed to load: {error}"
            ) from error
        _check_collisions(
            app, entry_point.name, view_functions_before, rules_before, owners
        )
        for endpoint in app.view_functions:
            owners.setdefault(endpoint, f"the plugin {entry_point.name}")
        loaded.append(
            LoadedPlugin(
                entry_point.name,
                plugin,
                _mounted_resources(app, view_functions_before),
            )
        )
    app.extensions[PLUGINS_EXTENSION] = loaded


def get_loaded_plugins(app):
    """
    Returns the plugins mounted on the application sorted by priority.

    :param app: the cornflow Flask application
    :return: the list of :class:`LoadedPlugin`
    """
    return sorted(
        app.extensions.get(PLUGINS_EXTENSION, []), key=lambda p: p.priority
    )


def get_plugins_resources(app):
    """
    Returns the resources mounted by the plugins, without duplicated endpoints.

    :param app: the cornflow Flask application
    :return: the list of resources
    """
    resources = {}
    for loaded in get_loaded_plugins(app):
        for resource in loaded.resources:
            resources.setdefault(resource["endpoint"], resource)
    return list(resources.values())


def register_plugins_access(app):
    """
    Asks every plugin, by priority, to register its roles, views and
    permissions, and then leaves the permissions on its views exactly as its
    code declares them. :func:`load_plugins` refuses two plugins that mount
    the same endpoint, so each endpoint belongs to a single plugin; the
    ``claimed_endpoints`` guard below is only a safety net. Plugins without a
    ``register_access`` method are skipped and the permissions on their
    views are not touched.

    :param app: the cornflow Flask application
    """
    # Imported here as the commands import this module
    from cornflow.commands.permissions import sync_plugin_permissions_command

    claimed_endpoints = set()
    for loaded in get_loaded_plugins(app):
        own_resources = [
            resource
            for resource in loaded.resources
            if resource["endpoint"] not in claimed_endpoints
        ]
        claimed_endpoints.update(resource["endpoint"] for resource in loaded.resources)
        register_access = getattr(loaded.plugin, "register_access", None)
        if callable(register_access):
            app.logger.info(f"Registering the access of the plugin {loaded.name}")
            register_access(app)
            sync_plugin_permissions_command(loaded, own_resources)
