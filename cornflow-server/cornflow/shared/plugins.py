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

PLUGIN_ENTRY_POINT_GROUP = "cornflow.plugins"
PLUGINS_EXTENSION = "cornflow_plugins"


class CornflowPlugin:
    """
    Base class for the cornflow plugins.

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

        The default implementation does nothing: a plugin that does not
        override it has to register its access by itself, and cornflow does
        not touch the permissions on its views.

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


def load_plugins(app):
    """
    Loads and mounts the plugins published under the ``cornflow.plugins``
    entry point group, recording the resources each one mounts.

    :param app: the cornflow Flask application
    """
    loaded = []
    for entry_point in importlib.metadata.entry_points(group=PLUGIN_ENTRY_POINT_GROUP):
        plugin = entry_point.load()()
        view_functions_before = dict(app.view_functions)
        plugin.init_app(app)
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
    code declares them. Each endpoint belongs to the first plugin, by
    priority, that mounts it (the same rule as :func:`get_plugins_resources`).
    Plugins without a ``register_access`` method are skipped and the
    permissions on their views are not touched.

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
