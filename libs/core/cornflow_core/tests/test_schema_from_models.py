import unittest
import json
import os

from click.testing import CliRunner

from cornflow_core.cli.schema_from_models import schema_from_models

path_to_tests = os.path.dirname(os.path.abspath(__file__))


class SchemaFromModelsTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.models_path = self._get_path("./data/models")
        self.output_path = self._get_path(os.path.join(os.getcwd(), "test_output.json"))

    @staticmethod
    def import_schema(path):
        with open(path, "r") as fd:
            schema = json.load(fd)
        return schema

    @staticmethod
    def _get_path(rel_path):
        return os.path.join(path_to_tests, rel_path)

    def tearDown(self):
        if os.path.exists(self.output_path):
            os.remove(self.output_path)

    def test_base(self):
        runner = CliRunner()
        result = runner.invoke(
            schema_from_models, ["-p", self.models_path, "-o", self.output_path]
        )

        print(result.output)

        self.assertEqual(result.exit_code, 0)

        schema = self.import_schema(self._get_path(self.output_path))

        tables = {
            "instances": {
                "id": "string",
                "data": "object",
                "checks": "object",
                "name": "string",
                "description": "string",
            },
            "actions": {"id": "integer", "name": "string"},
            "permission_dag": {
                "id": "integer",
                "dag_id": "string",
                "user_id": "integer",
            },
            "permission_view": {
                "id": "integer",
                "action_id": "integer",
                "api_view_id": "integer",
                "role_id": "integer",
            },
        }
        required_instance = {"id", "name", "data_hash"}
        foreign_keys = [
            ("permission_dag", "dag_id", "deployed_dags.id"),
            ("permission_dag", "user_id", "users.id"),
            ("permission_view", "action_id", "actions.id"),
            ("permission_view", "api_view_id", "api_view.id"),
        ]
        for tab_name, tab_checks in tables.items():
            # All tables exist
            self.assertIn(tab_name, schema["properties"])
            # The properties have correct types
            for prop, type_prop in tab_checks.items():
                table_props = schema["properties"][tab_name]["items"]["properties"]
                self.assertIn(prop, table_props)
                self.assertIn("type", table_props.get(prop, {}).keys())
                self.assertEqual(
                    type_prop, table_props.get(prop, {}).get("type", "null")
                )
        # The foreign keys are correct
        for tab, key, foreign_key in foreign_keys:
            self.assertIn(
                "foreign_key", schema["properties"][tab]["items"]["properties"][key]
            )
            self.assertEqual(
                schema["properties"][tab]["items"]["properties"][key]["foreign_key"],
                foreign_key,
            )
        # The required property is correct
        self.assertEqual(
            required_instance,
            set(schema["properties"]["instances"]["items"]["required"]),
        )

    def test_ignore(self):
        runner = CliRunner()
        result = runner.invoke(
            schema_from_models,
            ["-p", self.models_path, "-o", self.output_path, "-i", "instance.py"],
        )

        self.assertEqual(result.exit_code, 0)

        schema = self.import_schema(self.output_path)

        self.assertNotIn("instances", schema["properties"].keys())
