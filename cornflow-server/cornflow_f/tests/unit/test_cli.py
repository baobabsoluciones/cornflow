"""
Tests for the CLI commands
"""

import pytest
from click.testing import CliRunner
from sqlalchemy.orm import Session
from cornflow_f.cli import cli

from cornflow_f.models import (
    ActionModel,
    PermissionViewRoleModel,
    RoleModel,
    UserModel,
    UserRoleModel,
    ViewModel,
)

from cornflow_f.shared.const import (
    DEFAULT_ROLES,
    DEFAULT_ACTIONS,
    DEFAULT_PERMISSIONS,
    PATH_BLACKLIST,
    HTTP_METHOD_TO_ACTION,
    DEFAULT_PERMISSIONS_BLACKLIST,
)


@pytest.fixture
def runner():
    """
    Fixture that provides a CLI runner
    """
    return CliRunner()


def test_create_user(runner, db_session: Session):
    """
    Test user creation through CLI
    """
    # Test successful user creation
    result = runner.invoke(
        cli,
        [
            "users",
            "create",
            "--username",
            "testuser",
            "--email",
            "test@example.com",
            "--password",
            "testpass",
            "--first-name",
            "Test",
            "--last-name",
            "User",
        ],
    )
    assert result.exit_code == 0
    assert "User testuser created successfully" in result.output

    # Verify user was created in database
    user = UserModel.get_by_username(db_session, "testuser")
    assert user is not None
    assert user.email == "test@example.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"

    # Test duplicate username
    result = runner.invoke(
        cli,
        [
            "users",
            "create",
            "--username",
            "testuser",
            "--email",
            "another@example.com",
            "--password",
            "testpass",
            "--first-name",
            "Another",
            "--last-name",
            "User",
        ],
    )
    assert result.exit_code == 0
    assert "Error: Username already exists" in result.output


def test_delete_user(runner, db_session: Session):
    """
    Test user deletion through CLI
    """
    # Create a user first
    user = UserModel(
        username="deleteuser",
        email="delete@example.com",
        password="testpass",
        first_name="Delete",
        last_name="User",
    )
    user.save(db_session)

    # Test successful deletion
    result = runner.invoke(cli, ["users", "delete", "--username", "deleteuser"])
    assert result.exit_code == 0
    assert "User deleteuser deleted successfully" in result.output

    # Verify user was deleted
    user = UserModel.get_by_username(db_session, "deleteuser")
    assert user is None

    # Test deleting non-existent user
    result = runner.invoke(cli, ["users", "delete", "--username", "nonexistent"])
    assert result.exit_code == 0
    assert "Error: User not found" in result.output


def test_create_role(runner, db_session: Session):
    """
    Test role creation through CLI
    """
    # Test successful role creation
    result = runner.invoke(
        cli,
        [
            "roles",
            "create",
            "--name",
            "testrole",
            "--description",
            "Test role description",
        ],
    )
    assert result.exit_code == 0
    assert "Role testrole created successfully" in result.output

    # Verify role was created
    role = RoleModel.get_by_name(db_session, "testrole")
    assert role is not None
    assert role.description == "Test role description"

    # Test duplicate role name
    result = runner.invoke(
        cli,
        [
            "roles",
            "create",
            "--name",
            "testrole",
            "--description",
            "Another description",
        ],
    )
    assert result.exit_code == 0
    assert "Error: Role already exists" in result.output


def test_delete_role(runner, db_session: Session):
    """
    Test role deletion through CLI
    """
    # Create a role first
    role = RoleModel(name="deleterole", description="Role to delete")
    role.save(db_session)

    # Test successful deletion
    result = runner.invoke(cli, ["roles", "delete", "--name", "deleterole"])
    assert result.exit_code == 0
    assert "Role deleterole deleted successfully" in result.output

    # Verify role was deleted
    role = RoleModel.get_by_name(db_session, "deleterole")
    assert role is None

    # Test deleting non-existent role
    result = runner.invoke(cli, ["roles", "delete", "--name", "nonexistent"])
    assert result.exit_code == 0
    assert "Error: Role not found" in result.output


def test_list_roles(runner, db_session: Session):
    """
    Test listing roles through CLI
    """
    # Create some roles
    roles = [
        RoleModel(name="role1", description="First role"),
        RoleModel(name="role2", description="Second role"),
    ]
    for role in roles:
        role.save(db_session)

    # Test listing roles
    result = runner.invoke(cli, ["roles", "list"])
    assert result.exit_code == 0
    assert "role1: First role" in result.output
    assert "role2: Second role" in result.output


def test_init_roles(runner, db_session: Session):
    """
    Test initializing default roles through CLI
    """
    # Test initializing default roles
    result = runner.invoke(cli, ["roles", "init"])
    assert result.exit_code == 0
    assert "Default roles initialized successfully" in result.output

    # Verify all default roles were created
    for role_data in DEFAULT_ROLES:
        role = RoleModel.get_by_name(db_session, role_data["name"])
        assert role is not None
        assert role.description == role_data["description"]

    # Test running init again (should not create duplicates)
    result = runner.invoke(cli, ["roles", "init"])
    assert result.exit_code == 0
    assert all(
        f"Role already exists: {role['name']}" in result.output
        for role in DEFAULT_ROLES
    )


def test_assign_role(runner, db_session: Session):
    """
    Test role assignment through CLI
    """
    # Create user and role first
    user = UserModel(
        username="assignuser",
        email="assign@example.com",
        password="testpass",
        first_name="Assign",
        last_name="User",
    )
    user.save(db_session)

    role = RoleModel(name="assignrole", description="Role to assign")
    role.save(db_session)

    # Test successful assignment
    result = runner.invoke(
        cli,
        ["assignments", "assign", "--username", "assignuser", "--role", "assignrole"],
    )
    assert result.exit_code == 0
    assert "Role assignrole assigned to user assignuser successfully" in result.output

    # Verify assignment was created
    assert UserRoleModel.has_role(db_session, user.id, role.id)

    # Test assigning non-existent user
    result = runner.invoke(
        cli,
        ["assignments", "assign", "--username", "nonexistent", "--role", "assignrole"],
    )
    assert result.exit_code == 0
    assert "Error: User not found" in result.output

    # Test assigning non-existent role
    result = runner.invoke(
        cli,
        ["assignments", "assign", "--username", "assignuser", "--role", "nonexistent"],
    )
    assert result.exit_code == 0
    assert "Error: Role not found" in result.output

    # Test assigning duplicate role
    result = runner.invoke(
        cli,
        ["assignments", "assign", "--username", "assignuser", "--role", "assignrole"],
    )
    assert result.exit_code == 0
    assert "Error: User already has this role" in result.output


def test_remove_role(runner, db_session: Session):
    """
    Test role removal through CLI
    """
    # Create user and role first
    user = UserModel(
        username="removeuser",
        email="remove@example.com",
        password="testpass",
        first_name="Remove",
        last_name="User",
    )
    user.save(db_session)

    role = RoleModel(name="removerole", description="Role to remove")
    role.save(db_session)

    # Create assignment
    user_role = UserRoleModel(user_id=user.id, role_id=role.id)
    user_role.save(db_session)

    # Test successful removal
    result = runner.invoke(
        cli,
        ["assignments", "remove", "--username", "removeuser", "--role", "removerole"],
    )
    assert result.exit_code == 0
    assert "Role removerole removed from user removeuser successfully" in result.output

    # Verify assignment was removed
    assert not UserRoleModel.has_role(db_session, user.id, role.id)

    # Test removing non-existent user
    result = runner.invoke(
        cli,
        ["assignments", "remove", "--username", "nonexistent", "--role", "removerole"],
    )
    assert result.exit_code == 0
    assert "Error: User not found" in result.output

    # Test removing non-existent role
    result = runner.invoke(
        cli,
        ["assignments", "remove", "--username", "removeuser", "--role", "nonexistent"],
    )
    assert result.exit_code == 0
    assert "Error: Role not found" in result.output

    # Test removing non-existent assignment
    result = runner.invoke(
        cli,
        ["assignments", "remove", "--username", "removeuser", "--role", "removerole"],
    )
    assert result.exit_code == 0
    assert "Error: User does not have this role" in result.output


def test_list_assignments(runner, db_session: Session):
    """
    Test listing role assignments through CLI
    """
    # Create user and roles
    user = UserModel(
        username="listuser",
        email="list@example.com",
        password="testpass",
        first_name="List",
        last_name="User",
    )
    user.save(db_session)

    roles = [
        RoleModel(name="listrole1", description="First list role"),
        RoleModel(name="listrole2", description="Second list role"),
    ]
    for role in roles:
        role.save(db_session)
        user_role = UserRoleModel(user_id=user.id, role_id=role.id)
        user_role.save(db_session)

    # Test listing assignments
    result = runner.invoke(cli, ["assignments", "list", "--username", "listuser"])
    assert result.exit_code == 0
    assert "listrole1: First list role" in result.output
    assert "listrole2: Second list role" in result.output

    # Test listing for non-existent user
    result = runner.invoke(cli, ["assignments", "list", "--username", "nonexistent"])
    assert result.exit_code == 0
    assert "Error: User not found" in result.output

    # Test listing for user with no roles
    user_no_roles = UserModel(
        username="noroles",
        email="noroles@example.com",
        password="testpass",
        first_name="No",
        last_name="Roles",
    )
    user_no_roles.save(db_session)
    result = runner.invoke(cli, ["assignments", "list", "--username", "noroles"])
    assert result.exit_code == 0
    assert "User noroles has no roles assigned" in result.output


def test_init_permissions(runner, db_session: Session):
    """
    Test initializing default permissions through CLI
    """
    # Test initializing default permissions
    result = runner.invoke(cli, ["permissions", "init"])
    assert result.exit_code == 0
    assert "Permission system initialization completed successfully" in result.output

    # Step 1: Verify all default roles were created
    for role_data in DEFAULT_ROLES:
        role = RoleModel.get_by_name(db_session, role_data["name"])
        assert role is not None
        assert role.description == role_data["description"]
        assert role.id == role_data["id"]

    # Step 2: Verify all default actions were created
    for action_data in DEFAULT_ACTIONS:
        action = ActionModel.get_by_name(db_session, action_data["name"])
        assert action is not None
        assert action.description == action_data["description"]
        assert action.id == action_data["id"]

    # Step 3: Verify views were created from app routes
    from cornflow_f.main import app

    # Get all routes from the FastAPI app
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                routes.append((route.path, method))

    # Count how many routes should be skipped due to blacklist
    expected_skipped = sum(
        1
        for path, _ in routes
        if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST)
    )

    # Verify the output mentions the correct number of skipped paths
    if expected_skipped > 0:
        assert f"Skipped {expected_skipped} documentation paths" in result.output

    # Verify views were created for non-blacklisted routes
    for path, _ in routes:
        # Skip documentation paths
        if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
            continue

        # Normalize path (remove path parameters)
        normalized_path = path.replace("{", "<").replace("}", ">")

        view = ViewModel.get_by_path(db_session, normalized_path)
        assert view is not None
        assert view.path == normalized_path
        assert view.name == normalized_path
        assert f"API endpoint: {path}" in view.description

    # Step 4: Verify all default permissions were created
    for path, http_action in routes:
        if http_action not in HTTP_METHOD_TO_ACTION:
            continue
        if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
            continue

        normalized_path = path.replace("{", "<").replace("}", ">")
        view = ViewModel.get_by_path(db_session, normalized_path)
        action_id = HTTP_METHOD_TO_ACTION[http_action]

        for role in DEFAULT_ROLES:
            # Check if this permission should be created based on DEFAULT_PERMISSIONS
            if (role["id"], action_id) in DEFAULT_PERMISSIONS:
                # Check if this permission is in the blacklist
                if (
                    role["id"],
                    action_id,
                    view.id,
                ) not in DEFAULT_PERMISSIONS_BLACKLIST:
                    permission = PermissionViewRoleModel.get_by_ids(
                        db_session, role["id"], action_id, view.id
                    )
                    assert permission is not None
                    assert permission.role_id == role["id"]
                    assert permission.action_id == action_id
                    assert permission.api_view_id == view.id

    # Test running init again (should not create duplicates)
    result = runner.invoke(cli, ["permissions", "init"])
    assert result.exit_code == 0

    # Verify that all roles, actions, and views are reported as already existing
    for role_data in DEFAULT_ROLES:
        assert f"Role already exists: {role_data['name']}" in result.output

    for action_data in DEFAULT_ACTIONS:
        assert f"Action already exists: {action_data['name']}" in result.output

    # Verify that permissions are reported as already existing
    for path, http_action in routes:
        if http_action not in HTTP_METHOD_TO_ACTION:
            continue
        if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
            continue

        normalized_path = path.replace("{", "<").replace("}", ">")
        view = ViewModel.get_by_path(db_session, normalized_path)
        action_id = HTTP_METHOD_TO_ACTION[http_action]

        for role in DEFAULT_ROLES:
            if (role["id"], action_id) in DEFAULT_PERMISSIONS:
                if (
                    role["id"],
                    action_id,
                    view.id,
                ) not in DEFAULT_PERMISSIONS_BLACKLIST:
                    role_obj = RoleModel.get_by_name(db_session, role["name"])
                    action_obj = ActionModel.get_by_id(db_session, action_id)
                    assert (
                        f"Permission already exists: {role_obj.name} can {action_obj.name} on {view.path}"
                        in result.output
                    )


def test_list_permissions(runner, db_session: Session):
    """
    Test listing permissions through CLI
    """
    # First initialize roles and permissions
    runner.invoke(cli, ["permissions", "init"])

    # Test listing permissions
    result = runner.invoke(cli, ["permissions", "list"])
    assert result.exit_code == 0
    assert "Available permissions:" in result.output

    # Get all routes from the FastAPI app to check view paths
    from cornflow_f.main import app
    from cornflow_f.shared.const import PATH_BLACKLIST, HTTP_METHOD_TO_ACTION

    # Get all routes from the FastAPI app
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                routes.append((route.path, method))

    # Check that all valid permissions are listed with the correct format
    for path, http_action in routes:
        if http_action not in HTTP_METHOD_TO_ACTION:
            continue
        if any(doc_path == path.lower() for doc_path in PATH_BLACKLIST):
            continue

        normalized_path = path.replace("{", "<").replace("}", ">")
        view = ViewModel.get_by_path(db_session, normalized_path)
        action_id = HTTP_METHOD_TO_ACTION[http_action]

        for role in DEFAULT_ROLES:
            # Check if this permission should be created based on DEFAULT_PERMISSIONS
            if (role["id"], action_id) in DEFAULT_PERMISSIONS:
                # Check if this permission is in the blacklist
                if (
                    role["id"],
                    action_id,
                    view.id,
                ) not in DEFAULT_PERMISSIONS_BLACKLIST:
                    role_obj = RoleModel.get_by_name(db_session, role["name"])
                    action_obj = ActionModel.get_by_id(db_session, action_id)
                    expected_output = (
                        f"- {role_obj.name} can {action_obj.name} on {view.path}"
                    )
                    assert expected_output in result.output

    # Test with no permissions (after clearing the database)
    db_session.query(PermissionViewRoleModel).delete()
    db_session.commit()

    result = runner.invoke(cli, ["permissions", "list"])
    assert result.exit_code == 0
    assert "No permissions found" in result.output

    # Test with invalid permissions (permissions with missing role, action, or view)
    # Create a permission with a non-existent role
    non_existent_role_id = 9999
    action = db_session.query(ActionModel).first()
    view = db_session.query(ViewModel).first()

    if action and view:
        invalid_permission = PermissionViewRoleModel(
            role_id=non_existent_role_id, action_id=action.id, api_view_id=view.id
        )
        db_session.add(invalid_permission)
        db_session.commit()

        result = runner.invoke(cli, ["permissions", "list"])
        assert result.exit_code == 0
        assert (
            f"- Invalid permission: role_id={non_existent_role_id}, action_id={action.id}, view_id={view.id}"
            in result.output
        )
