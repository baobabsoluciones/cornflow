"""
Unit test for the api views endpoint
"""

# Import from internal modules
from cornflow.endpoints import ApiViewListEndpoint, resources
from cornflow.shared.const import ROLES_MAP
from cornflow.tests.const import APIVIEW_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestApiViewListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.roles_with_access = ApiViewListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
            for view in resources
        ]
        self.items_to_check = ["name", "description", "url_rule"]

    def tearDown(self):
        super().tearDown()

    def test_get_api_view_authorized(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                APIVIEW_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            for item in range(len(self.payload)):
                for field in self.items_to_check:
                    self.assertEqual(
                        self.payload[item][field], response.json[item][field]
                    )

    def test_get_api_view_not_authorized(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    APIVIEW_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )

                self.assertEqual(403, response.status_code)
