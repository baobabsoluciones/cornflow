"""
Unit tests for the alarms endpoint.

This module contains tests for the alarms API endpoint functionality, including:
- Creating new alarms
- Retrieving alarm listings
- Validating alarm data and properties

Classes
-------
TestAlarmsEndpoint
    Tests for the alarms endpoint functionality
"""

# Imports from internal modules
import json
from cornflow.models import AlarmsModel
from cornflow.tests.const import ALARMS_URL
from cornflow.tests.custom_test_case import BaseTestCases, CustomTestCase


class TestAlarmsEndpoint(CustomTestCase):
    """
    Test cases for the alarms endpoint.

    This class tests the functionality of managing alarms, including:
    - Creating new alarms with various properties
    - Retrieving and validating alarm data
    - Checking alarm schema and criticality levels
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes test data including:
        - Base test case setup
        - URL endpoint configuration
        - Model and response field definitions
        - Test items to check
        """
        super().setUp()
        self.url = ALARMS_URL
        self.model = AlarmsModel
        self.response_items = {"id", "name", "description", "criticality", "schema"}
        self.items_to_check = ["name", "description", "schema", "criticality"]

    def test_post_alarm(self):
        """
        Test creating a new alarm.

        Verifies that an alarm can be created with:
        - A name
        - A description
        - A criticality level
        """
        payload = {
            "name": "Alarm 1",
            "description": "Description Alarm 1",
            "criticality": 1,
        }
        self.create_new_row(self.url, self.model, payload)

    def test_get_alarms(self):
        """
        Test retrieving multiple alarms.

        Verifies:
        - Retrieval of multiple alarms with different properties
        - Proper handling of alarms with and without schema
        - Correct validation of alarm data fields
        """
        data = [
            {"name": "Alarm 1", "description": "Description Alarm 1", "criticality": 1},
            {
                "name": "Alarm 2",
                "description": "Description Alarm 2",
                "criticality": 2,
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


class TestAlarmsDetailEndpoint(TestAlarmsEndpoint, BaseTestCases.DetailEndpoint):
    def setUp(self):
        super().setUp()
        self.idx = 0
        self.payload = {
            "name": "Alarm 1",
            "description": "Description Alarm 1",
            "criticality": 1,
        }

    def test_disable_alarm_detail(self):
        """
        The idea would be to read the alarm_id from the query and be able to disable the entire row for that alarm in the database.
        To check this, I would use an example data set of different alarms and, after giving a specific id, be able to return the same data set,
        excluding those related to the given alarm_id.

        Verifies:
        - Retrieval of a single alarm using its ID
        - Correct validation of alarm data fields

        """

        data = {
            "name": "Alarm 1",
            "description": "Description Alarm 1",
            "criticality": 1,
        }
        id = self.create_new_row(self.url, self.model, data)
        data = {
            "name": "Alarm 2",
            "description": "Description Alarm 2",
            "criticality": 1,
        }
        self.idx = id
        url = self.url + str(id) + "/"
        response = self.client.delete(
            url,
            data=json.dumps(data),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Object marked as disabled"})
        all_rows = AlarmsModel.query.all()
        for row in all_rows:
            if row.id == id:
                # We check deleted at has a value
                self.assertIsNotNone(row.deleted_at)
            else:
                self.assertIsNone(row.deleted_at)
