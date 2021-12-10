"""
Unit test for the actions endpoint
"""

# Import from libraries
from cornflow.endpoints import ActionListEndpoint
from cornflow.shared.const import ACTIONS_MAP, ROLES_MAP
from cornflow.tests.const import ACTIONS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestActionsListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.roles_with_access = ActionListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {"id": key, "name": value.replace("_", " ")}
            for key, value in ACTIONS_MAP.items()
        ]

    def tearDown(self):
        super().tearDown()

    def test_get_actions_authorized(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                ACTIONS_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertCountEqual(self.payload, response.json)

    def test_get_actions_not_authorized(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    ACTIONS_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )

                self.assertEqual(403, response.status_code)
