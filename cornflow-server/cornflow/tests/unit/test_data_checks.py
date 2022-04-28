"""
Unit test for the data check endpoint
"""

# Import from libraries
import json

# Import from internal modules
from cornflow.models import ExecutionModel, InstanceModel
from cornflow.tests.const import (
    INSTANCE_PATH,
    EXECUTION_PATH,
    EXECUTION_URL_NORUN,
    DATA_CHECK_URL_NORUN,
    INSTANCE_URL,
)
from cornflow.tests.custom_test_case import CustomTestCase


class TestDataChecksEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

        with open(INSTANCE_PATH) as f:
            payload = json.load(f)
        fk_id = self.create_new_row(INSTANCE_URL, InstanceModel, payload)
        self.model = ExecutionModel

        def load_file_fk(_file):
            with open(_file) as f:
                temp = json.load(f)
            temp["instance_id"] = fk_id
            return temp

        self.payload = {load_file_fk(EXECUTION_PATH)}

    def test_new_data_check_execution(self):
        exec_to_check_id = self.create_new_row(
            EXECUTION_URL_NORUN,
            self.model,
            payload=self.payload
        )
        payload = dict(
            name="test",
            config=dict(),
            execution_id=exec_to_check_id
        )
        response = self.create_new_row(
            DATA_CHECK_URL_NORUN,
            self.model,
            payload=payload,
            check_payload=False
        )
        row = self.model.query.get(response["id"])
        self.assertEqual(row.id, response["id"])

        self.assertEqual(row.name, payload["name"])
        self.assertEqual(row.config.get("execution_id"), exec_to_check_id)
        self.assertTrue(row.config.get("checks_only"))
        self.assertEqual(row.config.get("schema"), "solve_model_dag")
