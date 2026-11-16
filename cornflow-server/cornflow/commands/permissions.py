from flask import current_app
from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow.commands.auxiliar import (
    get_all_external,
    get_all_resources,
)
from cornflow.models import ViewModel, PermissionViewRoleModel
from cornflow.shared import db
from cornflow.shared.const import ALL_DEFAULT_ROLES, GET_ACTION
from cornflow.shared.plugins import get_plugins_resources
import click
from cornflow.shared.const import (
    ADMIN_ROLE,
    BASE_PERMISSION_ASSIGNATION,
    PLATFORM_ADMIN_ROLE,
    PLATFORM_ROLE_INHERITANCE,
)


def register_base_permissions_command(external_app: str = None, verbose: bool = False):
    """
    Register base permissions for the application.
    external_app: If provided, it will register the permissions for the external app.
    verbose: If True, it will print the permissions that are being registered.
    """
    # Get all resources, extra permissions, and custom roles actions
    resources_to_register, extra_permissions, custom_roles_actions = get_all_external(
        external_app
    )

    # Get all views in the database
    views_in_db = {view.name: view.id for view in ViewModel.get_all_objects()}
    permissions_in_db, permissions_in_db_keys = get_db_permissions()

    # Get all resources and roles with access
    resources_roles_with_access = get_all_resources(resources_to_register)

    # Get the new roles and base permissions assignation
    base_permissions_assignation = get_base_permissions(
        resources_roles_with_access, custom_roles_actions
    )
    # Get the permissions to register and delete
    permissions_tuples = get_permissions_in_code_as_tuples(
        resources_to_register,
        views_in_db,
        base_permissions_assignation,
        extra_permissions,
    )
    permissions_to_register = get_permissions_to_register(
        permissions_tuples, permissions_in_db_keys
    )
    permissions_to_delete = get_permissions_to_delete(
        permissions_tuples, resources_roles_with_access.keys(), permissions_in_db
    )
    # Plugin mode: the permissions on the plugin views are left as declared
    # by each plugin after it registers its access (its own roles may not
    # exist yet), see sync_plugin_permissions_command
    plugin_views = {
        views_in_db[res["endpoint"]]
        for res in get_plugins_resources(current_app)
        if res["endpoint"] in views_in_db
    }
    permissions_to_delete = [
        permission
        for permission in permissions_to_delete
        if permission.api_view_id not in plugin_views
    ]

    # Save the new permissions in the data
    save_and_delete_permissions(permissions_to_register, permissions_to_delete)

    if len(permissions_to_register) > 0:
        current_app.logger.info(
            f"Permissions registered: {len(permissions_to_register)}"
        )
    else:
        current_app.logger.info("No new permissions to register")

    if len(permissions_to_delete) > 0:
        current_app.logger.info(f"Permissions deleted: {len(permissions_to_delete)}")
    else:
        current_app.logger.info("No permissions to delete")


def sync_plugin_permissions_command(loaded_plugin, resources):
    """
    Leaves the permissions on the views mounted by a plugin exactly as its code
    declares them: the ``ROLES_WITH_ACCESS`` of each resource, with the actions
    of the plugin's own roles given by its ``get_custom_roles_actions``, plus
    the cornflow extra permissions on those views. The missing permissions are
    created and the ones not declared, including those added by hand, are
    deleted. The permissions on any other view are not touched, nor those on
    the views the plugin mounts with the name of a cornflow endpoint, which
    are managed as cornflow views.

    loaded_plugin: the plugin, as recorded by load_plugins.
    resources: the resources that belong to the plugin.
    """
    core_resources, extra_permissions, _ = get_all_external(None)
    core_endpoints = {res["endpoint"] for res in core_resources}
    views_in_db = {view.name: view.id for view in ViewModel.get_all_objects()}
    plugin_views = {
        res["endpoint"]: views_in_db[res["endpoint"]]
        for res in resources
        if res["endpoint"] not in core_endpoints and res["endpoint"] in views_in_db
    }
    if not plugin_views:
        return
    plugin_resources = [res for res in resources if res["endpoint"] in plugin_views]

    get_custom_roles_actions = getattr(
        loaded_plugin.plugin, "get_custom_roles_actions", None
    )
    custom_roles_actions = (
        get_custom_roles_actions() if callable(get_custom_roles_actions) else {}
    )
    try:
        base_permissions_assignation = get_base_permissions(
            get_all_resources(plugin_resources), custom_roles_actions
        )
    except ValueError as e:
        current_app.logger.error(
            f"The permissions of the plugin {loaded_plugin.name} are left as they "
            f"are: {e}"
        )
        return

    permissions_tuples = get_permissions_in_code_as_tuples(
        plugin_resources, plugin_views, base_permissions_assignation, extra_permissions
    )
    permissions_in_db, permissions_in_db_keys = get_db_permissions()
    plugin_view_ids = set(plugin_views.values())
    permissions_to_register = get_permissions_to_register(
        permissions_tuples, permissions_in_db_keys
    )
    permissions_to_delete = get_permissions_to_delete(
        permissions_tuples,
        plugin_views.keys(),
        [perm for perm in permissions_in_db if perm.api_view_id in plugin_view_ids],
    )
    save_and_delete_permissions(permissions_to_register, permissions_to_delete)

    if permissions_to_register or permissions_to_delete:
        current_app.logger.info(
            f"Permissions of the plugin {loaded_plugin.name}: "
            f"{len(permissions_to_register)} registered, "
            f"{len(permissions_to_delete)} deleted"
        )


def save_new_roles(new_roles_to_add):
    """
    Save the new roles in the database.
    new_roles_to_add: List of new roles to add.
    """
    if len(new_roles_to_add) > 0:
        db.session.bulk_save_objects(new_roles_to_add)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Integrity error on base permissions register: {e}"
            )
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(f"Unknown error on base permissions register: {e}")


def save_and_delete_permissions(permissions_to_register, permissions_to_delete):
    """
    Save and delete permissions in the database.
    permissions_to_register: List of permissions to register.
    permissions_to_delete: List of permissions to delete.
    """
    if len(permissions_to_register) > 0:
        db.session.bulk_save_objects(permissions_to_register)

    if len(permissions_to_delete) > 0:
        for permission in permissions_to_delete:
            db.session.delete(permission)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on base permissions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on base permissions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_view', 'id'), MAX(id)) FROM permission_view;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unknown error on base permissions sequence updating: {e}"
            )


def get_permissions_to_delete(permissions_tuples, resources_names, permissions_in_db):
    """
    Get the permissions to delete.
    """
    permissions_to_delete = [
        permission
        for permission in permissions_in_db
        if (permission.role_id, permission.action_id, permission.api_view_id)
        not in permissions_tuples
    ]

    return permissions_to_delete


def get_permissions_to_register(permissions_tuples, permissions_in_db_keys):
    """
    Get the permissions to register.
    """
    # Convert set of tuples to list of PermissionViewRoleModel objects
    return [
        PermissionViewRoleModel(
            {
                "role_id": role_id,
                "action_id": action_id,
                "api_view_id": api_view_id,
            }
        )
        for role_id, action_id, api_view_id in permissions_tuples
        if (role_id, action_id, api_view_id) not in permissions_in_db_keys
    ]


def _role_has_view_access(role, roles_with_access):
    """
    Whether a role should get access to a view. Each platform role is a
    counterpart of a client role (platform_admin/admin, platform_viewer/
    viewer, platform_planner/planner) and inherits access to every view its
    client counterpart can reach, on top of the platform-only views where it
    is listed explicitly. This keeps the endpoint declarations simple (they
    only need to list the client roles) while the platform roles follow.
    """
    if role in roles_with_access:
        return True
    client_counterpart = PLATFORM_ROLE_INHERITANCE.get(role)
    if client_counterpart is not None and client_counterpart in roles_with_access:
        return True
    return False


def get_permissions_in_code_as_tuples(
    resources_to_register, views_in_db, base_permissions_assignation, extra_permissions
):
    """
    Get the permissions in code as tuples.
    """
    # Create base permissions using a set to avoid duplicates
    permissions_tuples = set()

    # Add permissions from ROLES_WITH_ACCESS
    for role, action in base_permissions_assignation:
        for view in resources_to_register:
            if _role_has_view_access(role, view["resource"].ROLES_WITH_ACCESS):
                permissions_tuples.add((role, action, views_in_db[view["endpoint"]]))

    # Add permissions from extra_permissions. Each platform role also gets the
    # extras of its client counterpart, so the pair keeps exactly the same
    # access — this covers the extras declared by an external application too,
    # not only cornflow's own.
    platform_counterparts = {
        client_role: platform_role
        for platform_role, client_role in PLATFORM_ROLE_INHERITANCE.items()
    }
    for role, action, endpoint in extra_permissions:
        if endpoint not in views_in_db:
            continue
        permissions_tuples.add((role, action, views_in_db[endpoint]))
        platform_role = platform_counterparts.get(role)
        if platform_role is not None:
            permissions_tuples.add((platform_role, action, views_in_db[endpoint]))

    return permissions_tuples


def get_base_permissions(resources_roles_with_access, custom_roles_actions):
    """
    Get the new roles and base permissions assignation.
    resources_roles_with_access: Dictionary of resources and roles with access.
    custom_roles_actions: Dictionary mapping custom roles to their allowed actions.
    """
    # Get all custom roles (both new and existing) that appear in ROLES_WITH_ACCESS
    all_custom_roles_in_access = set(
        [
            role
            for roles in resources_roles_with_access.values()
            for role in roles
            if role not in ALL_DEFAULT_ROLES
        ]
    )

    # Validate that all custom roles are defined in custom_roles_actions
    undefined_roles = all_custom_roles_in_access - set(custom_roles_actions.keys())
    if undefined_roles:
        raise ValueError(
            f"The following custom roles are used in code but not defined in CUSTOM_ROLES_ACTIONS: {undefined_roles}. "
            f"Please define their allowed actions in the CUSTOM_ROLES_ACTIONS dictionary in shared/const.py."
        )

    # Create extended permission assignation including all custom roles
    # For custom roles, use the actions defined in custom_roles_actions
    custom_permissions = [
        (custom_role, action)
        for custom_role in all_custom_roles_in_access
        for action in custom_roles_actions[custom_role]
    ]

    base_permissions_assignation = BASE_PERMISSION_ASSIGNATION + custom_permissions

    return base_permissions_assignation


def get_db_permissions():
    """
    Get all permissions in the database.
    """
    permissions_in_db = [perm for perm in PermissionViewRoleModel.get_all_objects()]
    permissions_in_db_keys = [
        (perm.role_id, perm.action_id, perm.api_view_id) for perm in permissions_in_db
    ]

    return permissions_in_db, permissions_in_db_keys


def register_dag_permissions_command(
    open_deployment: int = None, verbose: bool = False
):
    """
    Register DAG permissions.
    open_deployment: If 1, it will register the permissions for the open deployment.
    verbose: If True, it will print the permissions that are being registered.
    """

    from flask import current_app
    from sqlalchemy.exc import DBAPIError, IntegrityError

    from cornflow.models import DeployedWorkflow, PermissionsDAG, UserModel
    from cornflow.shared import db

    if open_deployment is None:
        open_deployment = int(current_app.config["OPEN_DEPLOYMENT"])

    existing_permissions = [
        (permission.dag_id, permission.user_id)
        for permission in PermissionsDAG.get_all_objects()
    ]

    try:
        db.session.commit()
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on database commit: {e}")

    all_users = UserModel.get_all_users().all()
    all_dags = DeployedWorkflow.get_all_objects().all()

    if int(open_deployment) == 1:

        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user.id})
            for user in all_users
            for dag in all_dags
            if (dag.id, user.id) not in existing_permissions
        ]

    else:
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user.id})
            for user in all_users
            for dag in all_dags
            if (dag.id, user.id) not in existing_permissions
            and (user.is_service_user() or user.is_admin())
        ]

    if len(permissions) > 0:
        db.session.bulk_save_objects(permissions)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error on dag permissions register: {e}")
    except DBAPIError as e:
        db.session.rollback()
        current_app.logger.error(f"Unknown error on dag permissions register: {e}")

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_dag', 'id'), MAX(id)) FROM permission_dag;"
        )

        try:
            db.session.commit()
        except DBAPIError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unknown error on dag permissions sequence updating: {e}"
            )

    if verbose:
        click.echo(f"Workflow permissions registered")
        if len(permissions) > 0:
            current_app.logger.info(
                f"Workflow permissions registered: {len(permissions)}"
            )
        else:
            current_app.logger.info("No new Workflow permissions")

