"""
Unit test for the licenses endpoint.

This module contains test cases for the licenses functionality, which handles
software license management and validation.

Classes
-------
TestLicenses
    Test cases for license management functionality
"""

# Import from internal modules
from cornflow.models import LicenseModel
from cornflow.tests.const import LICENSES_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestLicenses(CustomTestCase):
    """
    Test cases for the licenses endpoint functionality.

    This class tests the management of software licenses, including creation,
    validation, and access control for license-related operations.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Base test setup from parent class
        - License-specific URL and model
        - Response items to check
        """
        super().setUp()
        self.url = LICENSES_URL
        self.model = LicenseModel
        self.response_items = {"id", "name", "description", "schema"}
        self.items_to_check = ["name", "description", "schema"]

    def test_post_license(self):
        """
        Tests license creation.

        Verifies that:
        - A new license can be created with valid data
        - The response contains the expected license information
        """
        payload = {"name": "License 1", "description": "Description License 1"}
        self.create_new_row(self.url, self.model, payload)

    def test_get_licenses(self):
        """
        Tests license retrieval.

        Verifies that:
        - Multiple licenses can be retrieved
        - The response contains all expected license data
        - The data structure matches the expected format
        """
        data = [
            {"name": "License 1", "description": "Description License 1"},
            {
                "name": "License 2",
                "description": "Description License 2",
                "schema": "solve_model_dag",
            },
        ]
        rows = self.get_rows(self.url, data, check_data=False)
        rows_data = list(rows.json)
        for i in range(len(data)):
            for key in self.get_keys_to_check(data[i]):
                self.assertIn(key, rows_data[i])
                if key in data[i]:
                    self.assertEqual(rows_data[i][key], data[i][key])
