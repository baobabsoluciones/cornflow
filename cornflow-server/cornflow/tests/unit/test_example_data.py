"""

"""

# General imports
import json

# Partial imports
from unittest.mock import patch


# Imports from internal modules
from cornflow.tests.const import EXAMPLE_URL, INSTANCE_PATH
from cornflow.tests.custom_test_case import CustomTestCase


class TestExampleDataEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.example = [
            {
                "name": "test_example_1",
                "description": "some_description",
                "instance": load_file(INSTANCE_PATH),
            },
            {
                "name": "test_example_2",
                "description": "some_description",
                "instance": load_file(INSTANCE_PATH),
            },
        ]
        self.url = EXAMPLE_URL
        self.schema_name = "solve_model_dag"

    def patch_af_client(self, Airflow_mock):
        af_client = Airflow_mock.return_value
        af_client.is_alive.return_value = True
        af_client.get_dag_info.return_value = {}
        af_client.get_one_variable.return_value = {
            "value": json.dumps(self.example),
            "key": self.schema_name,
        }
        af_client.get_all_schemas.return_value = [{"name": self.schema_name}]
        return af_client

    @patch("cornflow.endpoints.example_data.Airflow.from_config")
    def test_get_list_of_examples(self, airflow_init):
        af_client = self.patch_af_client(airflow_init)
        examples = self.get_one_row(
            f"{self.url}/{self.schema_name}/",
            {},
            expected_status=200,
            check_payload=False,
        )

        for pos, item in enumerate(examples):
            self.assertIn("name", item)
            self.assertEqual(self.example[pos]["name"], item["name"])
            self.assertIn("description", item)
            self.assertEqual(self.example[pos]["description"], item["description"])

    @patch("cornflow.endpoints.example_data.Airflow.from_config")
    def test_get_one_example(self, airflow_init):
        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        af_client = self.patch_af_client(airflow_init)
        keys_to_check = ["name", "examples"]
        example = self.get_one_row(
            f"{self.url}/{self.schema_name}/test_example_1/",
            {},
            expected_status=200,
            check_payload=False,
            keys_to_check=keys_to_check,
        )

        self.assertIn("name", example)
        self.assertEqual("test_example_1", example["name"])
        self.assertIn("description", example)
        self.assertIn("instance", example)
        self.assertEqual(load_file(INSTANCE_PATH), example["instance"])
