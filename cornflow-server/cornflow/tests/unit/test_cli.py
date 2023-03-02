import configparser
import os

from click.testing import CliRunner
from cornflow import create_app
from cornflow.cli import cli
from cornflow_core.models import ActionBaseModel
from cornflow_core.shared import db
from flask_testing import TestCase


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
        actions = ActionBaseModel.get_all_objects().all()
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

        pass
