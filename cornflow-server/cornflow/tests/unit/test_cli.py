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


class CLITests(TestCase):
    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        app = create_app("testing")
        return app

    def test_entry_point(self):
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
        runner = CliRunner()
        result = runner.invoke(cli, ["actions", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the actions", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the actions", result.output)

    def test_actions(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["actions", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        actions = ActionModel.get_all_objects().all()
        self.assertEqual(len(actions), 5)

    def test_config_entrypoint(self):
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
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ENV", result.output)
        self.assertIn("testing", result.output)

    def test_config_get(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "get", "-k", "ENV"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("testing", result.output)

    def test_config_save(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "save", "-p", "./"])
        self.assertEqual(result.exit_code, 0)

        config = configparser.ConfigParser()
        config.read("config.cfg")
        self.assertEqual(config["configuration"]["ENV"], "testing")

        os.remove("config.cfg")

    def test_roles_entrypoint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["roles", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the roles", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initializes the roles with the default roles", result.output)

    def test_roles_init_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["roles", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        roles = RoleModel.get_all_objects().all()
        self.assertEqual(len(roles), 4)

    def test_views_entrypoint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["views", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the views", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the views", result.output)

    def test_views_init_command(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["views", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        views = ViewModel.get_all_objects().all()
        self.assertEqual(len(views), 50)

    def test_permissions_entrypoint(self):
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
        runner = CliRunner()
        result = runner.invoke(cli, ["permissions", "init", "-v"])
        self.assertEqual(result.exit_code, 0)
        actions = ActionModel.get_all_objects().all()
        roles = RoleModel.get_all_objects().all()
        views = ViewModel.get_all_objects().all()
        permissions = PermissionViewRoleModel.get_all_objects().all()
        self.assertEqual(len(actions), 5)
        self.assertEqual(len(roles), 4)
        self.assertEqual(len(views), 50)
        self.assertEqual(len(permissions), 551)

    def test_permissions_base_command(self):
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
        self.assertEqual(len(views), 50)
        self.assertEqual(len(permissions), 551)

    def test_service_entrypoint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["service", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to run the cornflow service", result.output)
        self.assertIn("init", result.output)
        self.assertIn("Initialize the service", result.output)

    def test_users_entrypoint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["users", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Commands to manage the users", result.output)
        self.assertIn("create", result.output)
        self.assertIn("Create a user", result.output)

    def test_users_create_entrypoint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["users", "create", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("service", result.output)
        self.assertIn("Create a service user", result.output)

    def test_service_user_help(self):
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
