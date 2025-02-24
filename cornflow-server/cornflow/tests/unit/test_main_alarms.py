"""

"""

import json

# Imports from internal modules
from cornflow.models import MainAlarmsModel, AlarmsModel
from cornflow.tests.const import MAIN_ALARMS_URL, ALARMS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestMainAlarmsEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = MAIN_ALARMS_URL
        self.model = MainAlarmsModel
        self.response_items = {"id", "message", "criticality", "schema", "id_alarm"}
        self.items_to_check = ["message", "schema", "criticality", "id_alarm"]
        payload = {
            "name": "Alarm 1",
            "description": "Description Alarm 1",
            "criticality": 1,
        }
        self.id_alarm = self.client.post(
            ALARMS_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        ).json["id"]

    def test_post_main_alarm(self):
        payload = {
            "message": "Message Main Alarm 1",
            "criticality": 1,
            "id_alarm": self.id_alarm,
        }
        self.create_new_row(self.url, self.model, payload)

    def test_get_main_alarms(self):
        data = [
            {
                "message": "Message Main Alarm 1",
                "criticality": 1,
                "id_alarm": self.id_alarm,
            },
            {
                "message": "Message Main Alarm 2",
                "criticality": 2,
                "schema": "solve_model_dag",
                "id_alarm": self.id_alarm,
            },
        ]
        keys_to_check = ["schema", "id_alarm", "criticality", "id", "message"]
        rows = self.get_rows(
            self.url, data, check_data=False, keys_to_check=keys_to_check
        )
        rows_data = list(rows.json)
        for i in range(len(data)):
            for key in self.get_keys_to_check(data[i]):
                self.assertIn(key, rows_data[i])
                if key in data[i]:
                    self.assertEqual(rows_data[i][key], data[i][key])
