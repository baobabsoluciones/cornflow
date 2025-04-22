"""
Integration tests for role-permission cascade behavior
"""

from sqlalchemy.orm import Session
from cornflow_f.models import RoleModel, PermissionViewRoleModel
from cornflow_f.cli import cli
from click.testing import CliRunner
from cornflow_f.shared.const import DEFAULT_ROLES
from cornflow_f.tests.fixtures import auth_headers, test_user, runner


def test_role_deletion_cascade_permissions_cli(client, runner, db_session: Session):
    """
    Test that deleting a role through the CLI cascades to delete all associated permissions

    Steps:
    1. Initialize the permissions system
    2. Delete a role through the CLI
    3. Verify that all permissions for that role have been deleted
    """
    # Step 1: Initialize the permissions system
    result = runner.invoke(cli, ["permissions", "init"])
    assert result.exit_code == 0
    assert "Permission system initialization completed successfully" in result.output

    # Get a role to delete (use the first default role)
    role_to_delete = DEFAULT_ROLES[0]
    role = RoleModel.get_by_name(db_session, role_to_delete["name"])
    assert role is not None

    # Count permissions for this role before deletion
    permissions_before = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == role.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert permissions_before > 0, "No permissions found for the role before deletion"

    # Step 2: Delete the role
    result = runner.invoke(cli, ["roles", "delete", "--name", role.name])
    assert result.exit_code == 0
    assert f"Role {role.name} deleted successfully" in result.output

    # Step 3: Verify that all permissions for that role have been deleted
    permissions_after = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == role.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert permissions_after == 0, "Permissions still exist for the deleted role"

    # Verify that the role itself is deleted
    deleted_role = RoleModel.get_by_name(db_session, role.name)
    assert deleted_role is None, "Role still exists after deletion"

    # Verify that permissions for other roles still exist
    other_role = DEFAULT_ROLES[1]
    other_role_obj = RoleModel.get_by_name(db_session, other_role["name"])
    assert other_role_obj is not None, "Other role was deleted"

    other_permissions = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == other_role_obj.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert other_permissions > 0, "Permissions for other roles were deleted"


def test_role_deletion_cascade_permissions_api(
    client, runner, db_session: Session, auth_headers
):
    """
    Test that deleting a role through the REST API cascades to delete all associated permissions

    Steps:
    1. Initialize the permissions system
    2. Delete a role through the REST API
    3. Verify that all permissions for that role have been deleted
    """
    # Step 1: Initialize the permissions system
    result = runner.invoke(cli, ["permissions", "init"])
    assert result.exit_code == 0
    assert "Permission system initialization completed successfully" in result.output

    # Get a role to delete (use the first default role)
    role_to_delete = DEFAULT_ROLES[0]
    role = RoleModel.get_by_name(db_session, role_to_delete["name"])
    assert role is not None

    # Count permissions for this role before deletion
    permissions_before = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == role.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert permissions_before > 0, "No permissions found for the role before deletion"

    # Step 2: Delete the role through the REST API
    response = client.delete(f"/roles/{role.id}", headers=auth_headers)
    assert response.status_code == 204, f"Failed to delete role: {response.text}"

    # Step 3: Verify that all permissions for that role have been deleted
    permissions_after = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == role.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert permissions_after == 0, "Permissions still exist for the deleted role"

    # Verify that the role itself is deleted
    deleted_role = RoleModel.get_by_name(db_session, role.name)
    assert deleted_role is None, "Role still exists after deletion"

    # Verify that permissions for other roles still exist
    other_role = DEFAULT_ROLES[1]
    other_role_obj = RoleModel.get_by_name(db_session, other_role["name"])
    assert other_role_obj is not None, "Other role was deleted"

    other_permissions = (
        db_session.query(PermissionViewRoleModel)
        .filter(
            PermissionViewRoleModel.role_id == other_role_obj.id,
            PermissionViewRoleModel.deleted_at.is_(None),
        )
        .count()
    )
    assert other_permissions > 0, "Permissions for other roles were deleted"
