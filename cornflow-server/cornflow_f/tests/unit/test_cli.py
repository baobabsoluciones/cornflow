"""
Tests for the CLI commands
"""

import pytest
from click.testing import CliRunner
from sqlalchemy.orm import Session
from cornflow_f.cli import cli
from cornflow_f.models.user import UserModel
from cornflow_f.models.role import RoleModel
from cornflow_f.models.user_role import UserRoleModel
from cornflow_f.shared.const import DEFAULT_ROLES


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
