"""
Permission management commands
"""

import click
from cornflow_f.database import get_db
from cornflow_f.models import RoleModel, ActionModel, PermissionViewRoleModel, ViewModel
from cornflow_f.shared.const import (
    DEFAULT_ACTIONS,
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    HTTP_METHOD_TO_ACTION,
    PATH_BLACKLIST,
)


@click.group()
def permissions():
    """
    Permission management commands
    """
    pass


@permissions.command()
def init():
    """
    Initialize the complete permissions system:
    1. Create default roles
    2. Create default actions
    3. Create views from app routes
    4. Create base permissions
    """
    db = next(get_db())
    try:
        # Step 1: Create default roles
        click.echo("Step 1: Creating default roles...")
        for role_data in DEFAULT_ROLES:
            if not RoleModel.exists_by_name(db, role_data["name"]):
                role = RoleModel(**role_data)
                role.save(db)
                click.echo(f"Created role: {role.name}")
            else:
                click.echo(f"Role already exists: {role_data['name']}")

        # Step 2: Create default actions
        click.echo("\nStep 2: Creating default actions...")
        for action_data in DEFAULT_ACTIONS:
            if not ActionModel.exists_by_name(db, action_data["name"]):
                action = ActionModel(**action_data)
                action.save(db)
                click.echo(f"Created action: {action.name}")
            else:
                click.echo(f"Action already exists: {action_data['name']}")

        # Step 3: Create views from app routes
        click.echo("\nStep 3: Creating views from app routes...")
        from cornflow_f.main import app

        # Get all routes from the FastAPI app
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    routes.append((route.path, method))

        click.echo(f"Found {len(routes)} routes in the application")

        # Create views for each route if they don't exist
        skipped_paths = 0
        for path, _ in routes:
            # Skip documentation paths
            if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
                skipped_paths += 1
                continue

            # Normalize path (remove path parameters)
            normalized_path = path.replace("{", "<").replace("}", ">")

            if not ViewModel.exists_by_path(db, normalized_path):
                view = ViewModel(
                    name=normalized_path,
                    path=normalized_path,
                    description=f"API endpoint: {path}",
                )
                view.save(db)
                click.echo(f"Created view: {view.path}")
            else:
                click.echo(f"View already exists: {normalized_path}")

        if skipped_paths > 0:
            click.echo(f"Skipped {skipped_paths} documentation paths")

        # Step 4: Create base permissions
        click.echo("\nStep 4: Creating base permissions...")

        permissions_to_create = []

        for path, http_action in routes:
            if http_action not in HTTP_METHOD_TO_ACTION:
                continue
            if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
                continue

            normalized_path = path.replace("{", "<").replace("}", ">")

            view = ViewModel.get_by_path(db, normalized_path)

            action_id = HTTP_METHOD_TO_ACTION[http_action]

            permissions_to_create += [
                (role["id"], action_id, view.id)
                for role in DEFAULT_ROLES
                if (role["id"], action_id) in DEFAULT_PERMISSIONS
            ]

        for perm_to_create in permissions_to_create:
            permission = PermissionViewRoleModel.get_by_ids(
                db, perm_to_create[0], perm_to_create[1], perm_to_create[2]
            )

            if not permission:
                permission = PermissionViewRoleModel(
                    role_id=perm_to_create[0],
                    action_id=perm_to_create[1],
                    api_view_id=perm_to_create[2],
                )
                permission.save(db)
                click.echo(
                    f"Created permission: {permission.role.name} can {permission.action.name} on {permission.view.path}"
                )
            else:
                click.echo(
                    f"Permission already exists: {permission.role.name} can {permission.action.name} on {permission.view.path}"
                )

        click.echo("\nPermission system initialization completed successfully")
    except Exception as e:
        click.echo(f"Error initializing permission system: {str(e)}")


@permissions.command()
def list():
    """
    List all permissions
    """
    db = next(get_db())
    try:
        permissions = (
            db.query(PermissionViewRoleModel)
            .filter(PermissionViewRoleModel.deleted_at.is_(None))
            .all()
        )

        if not permissions:
            click.echo("No permissions found")
            return

        click.echo("Available permissions:")
        for permission in permissions:
            role = (
                db.query(RoleModel).filter(RoleModel.id == permission.role_id).first()
            )
            action = (
                db.query(ActionModel)
                .filter(ActionModel.id == permission.action_id)
                .first()
            )
            view = (
                db.query(ViewModel)
                .filter(ViewModel.id == permission.api_view_id)
                .first()
            )

            if role and action and view:
                click.echo(f"- {role.name} can {action.name} on {view.path}")
            else:
                click.echo(
                    f"- Invalid permission: role_id={permission.role_id}, action_id={permission.action_id}, view_id={permission.api_view_id}"
                )
    except Exception as e:
        click.echo(f"Error listing permissions: {str(e)}")


@permissions.command()
@click.option("--role", prompt=True, help="Role name to assign permissions to")
@click.option(
    "--action", prompt=True, help="Action name (read, create, update, delete)"
)
def assign_permission(role: str, action: str):
    """
    Assign a permission to a role for all views
    """
    db = next(get_db())
    try:
        # Get the role
        role_obj = RoleModel.get_by_name(db, role)
        if not role_obj:
            click.echo(f"Error: Role '{role}' not found")
            return

        # Get the action
        action_obj = ActionModel.get_by_name(db, action)
        if not action_obj:
            click.echo(f"Error: Action '{action}' not found")
            return

        # Get all views
        from cornflow_f.models.view import ViewModel

        views = db.query(ViewModel).filter(ViewModel.deleted_at.is_(None)).all()

        if not views:
            click.echo("No views found. Run 'permissions init' first.")
            return

        # Create permissions for each view
        from cornflow_f.models.permission_view_role import PermissionViewRoleModel

        count = 0

        for view in views:
            # Check if permission already exists
            existing_permission = (
                db.query(PermissionViewRoleModel)
                .filter(
                    PermissionViewRoleModel.role_id == role_obj.id,
                    PermissionViewRoleModel.action_id == action_obj.id,
                    PermissionViewRoleModel.api_view_id == view.id,
                    PermissionViewRoleModel.deleted_at.is_(None),
                )
                .first()
            )

            if not existing_permission:
                permission = PermissionViewRoleModel(
                    role_id=role_obj.id,
                    action_id=action_obj.id,
                    api_view_id=view.id,
                )
                permission.save(db)
                count += 1

        click.echo(
            f"Created {count} permissions for role '{role}' with action '{action}'"
        )
    except Exception as e:
        click.echo(f"Error assigning permissions: {str(e)}")
