"""

"""
from cornflow.shared.const import BASE_ACTIONS
from cornflow.tests.const import ACTIONS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestActionsListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_permissions_super_admin(self):
        token = self.create_super_admin()
        response = self.client.get(
            ACTIONS_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(200, response.status_code)
        actions_list = [
            {"id": key, "name": value.replace("_", " ")}
            for key, value in BASE_ACTIONS.items()
        ]
        self.assertCountEqual(actions_list, response.json)

    def test_get_permissions_admin(self):
        token = self.create_admin()
        response = self.client.get(
            ACTIONS_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(200, response.status_code)
        actions_list = [
            {"id": key, "name": value.replace("_", " ")}
            for key, value in BASE_ACTIONS.items()
        ]
        self.assertCountEqual(actions_list, response.json)

    def test_get_no_permissions(self):
        response = self.client.get(
            ACTIONS_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(403, response.status_code)
