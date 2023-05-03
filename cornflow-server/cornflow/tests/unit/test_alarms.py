"""

"""
# Imports from internal modules
from cornflow.models import AlarmsModel
from cornflow.tests.const import ALARMS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestAlarmsEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = ALARMS_URL
        self.model = AlarmsModel
        self.response_items = {"id", "name", "description", "criticality", "schema"}
        self.items_to_check = ["name", "description", "schema", "criticality"]

    def test_post_alarm(self):
        payload = {"name": "Alarm 1", "description": "Description Alarm 1", "criticality": 1}
        self.create_new_row(self.url, self.model, payload)

    def test_get_alarms(self):
        data = [
            {"name": "Alarm 1", "description": "Description Alarm 1", "criticality": 1},
            {"name": "Alarm 2", "description": "Description Alarm 2", "criticality": 2, "schema": "solve_model_dag"},
        ]
        rows = self.get_rows(
            self.url,
            data,
            check_data=False
        )
        rows_data = list(rows.json)
        for i in range(len(data)):
            for key in self.get_keys_to_check(data[i]):
                self.assertIn(key, rows_data[i])
                if key in data[i]:
                    self.assertEqual(rows_data[i][key], data[i][key])


