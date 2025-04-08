"""
Unit tests for the Cornflow CLI commands.

This module contains tests for the command-line interface functionality, including:

- Entry point commands and help messages
- Actions management commands
- Configuration management commands
- Roles management commands
- Views management commands
- Permissions management commands
- Service management commands
- User management commands

The tests verify both the command structure and the actual functionality
of each command, ensuring proper database operations and state changes.
"""

import configparser
import os

from click.testing import CliRunner
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.models import (
    ActionModel,
    RoleModel,
    ViewModel,
    PermissionViewRoleModel,
)
from cornflow.models import UserModel
from cornflow.shared import db
from cornflow.shared.exceptions import NoPermission, ObjectDoesNotExist
from cornflow.endpoints import resources, alarms_resources


class CLITests(TestCase):
    """
    Test suite for Cornflow CLI functionality.

    This class tests all CLI commands and their effects on the system, including:

    - Command help messages and documentation
    - Actions initialization and management
    - Configuration variable handling
    - Role management and initialization
    - View registration and management
    - Permission system setup and validation
    - Service initialization
    - User creation and management

    Each test method focuses on a specific command or group of related commands,
    verifying both the command interface and its actual effects on the system.
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Creates all database tables required for testing.
        """
        db.create_all()

    def tearDown(self):
        """
        Clean up test environment after each test.

        Removes database session and drops all tables.
        """
        db.session.remove()
        db.drop_all()

    def create_app(self):
        """
        Create and configure the Flask application for testing.

        :return: The configured Flask application instance
        :rtype: Flask
        """
        app = create_app("testing")
        return app

    def test_entry_point(self):
        """
        Test the main CLI entry point and help command.

        Verifies:

        - Command execution success
        - Presence of all main command groups
        - Help message content and formatting
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands in the cornflow cli", result.output)
        self.assertIn("Show this message and exit.", result.output)
        self.assertIn("actions", result.output)
        self.assertIn("Commands to manage the actions", result.output)
        self.assertIn("config", result.output)
        self.assertIn("Commands to manage the configuration variables", result.output)
        self.assertIn("migrations", result.output)
        self.assertIn("Commands to manage the migrations", result.output)
        self.assertIn("permissions", result.output)
        self.assertIn("Commands to manage the permissions", result.output)
        self.assertIn("roles", result.output)
        self.assertIn("Commands to manage the roles", result.output)
        self.assertIn("service", result.output)
        self.assertIn("Commands to run the cornflow service", result.output)
        self.assertIn("users", result.output)
        self.assertIn("Commands to manage the users", result.output)
        self.assertIn("views", result.output)
        self.assertIn("Commands to manage the views", result.output)

    def test_actions_entry_point(self):
        """
        Test the actions command group entry point.

        Verifies:

        - Actions command help message
        - Presence of init subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["actions", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the actions", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the actions", result.output)

    def test_actions(self):
        """
        Test the actions initialization command.

        Verifies:

        - Successful action initialization
        - Correct number of actions created
        - Database state after initialization
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["actions", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        actions = ActionModel.get_all_objects().all()
        self.assertEqual(len(actions), 5)

    def test_config_entrypoint(self):
        """
        Test the config command group entry point.

        Verifies:

        - Config command help message
        - Presence of all config subcommands
        - Command descriptions
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the configuration variables", result.output)
        self.assertIn("get", result.output)
        self.assertIn("Get the value of a configuration variable", result.output)
        self.assertIn("list", result.output)
        self.assertIn("List the configuration variables", result.output)
        self.assertIn("save", result.output)
        self.assertIn("Save the configuration variables to a file", result.output)

    def test_config_list(self):
        """
        Test the config list command.

        Verifies:

        - Successful listing of configuration variables
        - Presence of key configuration items
        - Correct values in testing environment
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ENV", result.output)
        self.assertIn("testing", result.output)

    def test_config_get(self):
        """
        Test the config get command.

        Verifies:

        - Successful retrieval of specific config value
        - Correct value returned for ENV variable
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "get", "-k", "ENV"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("testing", result.output)

    def test_config_save(self):
        """
        Test the config save command.

        Verifies:

        - Successful configuration file creation
        - Correct content in saved file
        - Proper file cleanup after test
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "save", "-p", "./"])
        self.assertEqual(result.exit_code, 0)

        config = configparser.ConfigParser()
        config.read("config.cfg")
        self.assertEqual(config["configuration"]["ENV"], "testing")

        os.remove("config.cfg")

    def test_roles_entrypoint(self):
        """
        Test the roles command group entry point.

        Verifies:

        - Roles command help message
        - Presence of init subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["roles", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the roles", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initializes the roles with the default roles", result.output)

    def test_roles_init_command(self):
        """
        Test the roles initialization command.

        Verifies:

        - Successful role initialization
        - Correct number of default roles created
        - Database state after initialization
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["roles", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        roles = RoleModel.get_all_objects().all()
        self.assertEqual(len(roles), 4)

    def test_views_entrypoint(self):
        """
        Test the views command group entry point.

        Verifies:

        - Views command help message
        - Presence of init subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["views", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the views", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the views", result.output)

    def test_views_init_command(self):
        """
        Test the views initialization command.

        Verifies:

        - Successful view initialization
        - Correct number of views created
        - Database state after initialization
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["views", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        views = ViewModel.get_all_objects().all()
        self.assertEqual(len(views), (len(resources) + len(alarms_resources)))

    def test_permissions_entrypoint(self):
        """
        Test the permissions command group entry point.

        Verifies:

        - Permissions command help message
        - Presence of all subcommands
        - Command descriptions
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["permissions", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the permissions", result.output)
        self.assertIn("init", result.output)
        self.assertIn(
            "Creates the actions, views, roles and permissions", result.output
        )
        self.assertIn("base", result.output)
        self.assertIn("Initialize the base permissions", result.output)

    def test_permissions_init(self):
        """
        Test the permissions initialization command.

        Verifies:

        - Successful initialization of all permission components
        - Correct number of actions, roles, views, and permissions
        - Database state after initialization
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["permissions", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        actions = ActionModel.get_all_objects().all()
        roles = RoleModel.get_all_objects().all()
        views = ViewModel.get_all_objects().all()
        permissions = PermissionViewRoleModel.get_all_objects().all()
        self.assertEqual(len(actions), 5)
        self.assertEqual(len(roles), 4)
        self.assertEqual(len(views), (len(resources) + len(alarms_resources)))
        self.assertEqual(len(permissions), 562)

    def test_permissions_base_command(self):
        """
        Test the base permissions initialization command.

        Verifies:

        - Successful initialization of base permissions
        - Correct setup of all permission components
        - Database state consistency
        """
        runner = CliRunner()
        runner.invoke(cli, ["actions", "init", "-v"])
        runner.invoke(cli, ["roles", "init", "-v"])
        runner.invoke(cli, ["views", "init", "-v"])
        result = runner.invoke(cli, ["permissions", "base", "-v"])
        self.assertEqual(result.exit_code, 0)
        actions = ActionModel.get_all_objects().all()
        roles = RoleModel.get_all_objects().all()
        views = ViewModel.get_all_objects().all()
        permissions = PermissionViewRoleModel.get_all_objects().all()
        self.assertEqual(len(actions), 5)
        self.assertEqual(len(roles), 4)
        self.assertEqual(len(views), (len(resources) + len(alarms_resources)))
        self.assertEqual(len(permissions), 562)

    def test_service_entrypoint(self):
        """
        Test the service command group entry point.

        Verifies:

        - Service command help message
        - Presence of init subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["service", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to run the cornflow service", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the service", result.output)

    def test_users_entrypoint(self):
        """
        Test the users command group entry point.

        Verifies:

        - Users command help message
        - Presence of create subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["users", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the users", result.output)
        self.assertIn("create", result.output)
        self.assertIn("Create a user", result.output)

    def test_users_create_entrypoint(self):
        """
        Test the users create command entry point.

        Verifies:

        - Create command help message
        - Presence of service subcommand
        - Command description accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["users", "create", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("service", result.output)
        self.assertIn("Create a service user", result.output)

    def test_service_user_help(self):
        """
        Test the service user creation help command.

        Verifies:

        - Help message content
        - Required parameter descriptions
        - Parameter documentation accuracy
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["users", "create", "service", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("The username of the user", result.output)
        self.assertIn("username", result.output)
        self.assertIn("The password of the user", result.output)
        self.assertIn("password", result.output)
        self.assertIn("The email of the user", result.output)
        self.assertIn("email", result.output)

    def test_service_user_command(self):
        """
        Test service user creation command.

        Verifies:

        - Successful service user creation
        - Correct user attributes
        - Service role assignment
        - Service user status verification
        """
        runner = CliRunner()
        self.test_roles_init_command()
        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "service",
                "-u",
                "test",
                "-p",
                "testPassword1!",
                "-e",
                "test@test.org",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        user = UserModel.get_one_user_by_email("test@test.org")
        self.assertEqual(user.username, "test")
        self.assertEqual(user.email, "test@test.org")
        self.assertEqual(user.roles, {4: "service"})
        self.assertTrue(user.is_service_user())

    def test_viewer_user_command(self):
        """
        Test viewer user creation command.

        Verifies:

        - Successful viewer user creation
        - Correct user attributes
        - Viewer role assignment
        - Service user status check
        """
        runner = CliRunner()
        self.test_roles_init_command()
        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "viewer",
                "-u",
                "test",
                "-p",
                "testPassword1!",
                "-e",
                "test@test.org",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        user = UserModel.get_one_user_by_email("test@test.org")
        self.assertEqual(user.username, "test")
        self.assertEqual(user.email, "test@test.org")
        self.assertEqual(user.roles, {1: "viewer"})
        self.assertFalse(user.is_service_user())

    def test_generate_token(self):
        runner = CliRunner()

        self.test_roles_init_command()

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "viewer",
                "-u",
                "viewer_user",
                "-p",
                "testPassword1!",
                "-e",
                "viewer@test.org",
            ],
        )

        self.assertEqual(result.exit_code, 0)

        user_id = UserModel.get_one_user_by_username("viewer_user").id

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "service",
                "-u",
                "test",
                "-p",
                "testPassword1!",
                "-e",
                "test@test.org",
            ],
        )

        self.assertEqual(result.exit_code, 0)

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "token",
                "-i",
                user_id,
                "-u",
                "test",
                "-p",
                "testPassword1!",
            ],
        )

        self.assertIn("ey", result.output)

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "token",
                "-i",
                user_id,
                "-u",
                "test",
                "-p",
                "Otherpassword",
            ],
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIsInstance(result.exception, NoPermission)

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "token",
                "-i",
                user_id,
                "-u",
                "viewer_user",
                "-p",
                "testPassword1!",
            ],
        )

        self.assertIsInstance(result.exception, NoPermission)

        result = runner.invoke(
            cli,
            [
                "users",
                "create",
                "token",
                "-i",
                100,
                "-u",
                "test",
                "-p",
                "testPassword1!",
            ],
        )

        self.assertIsInstance(result.exception, ObjectDoesNotExist)
