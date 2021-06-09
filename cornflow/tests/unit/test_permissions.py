"""
Unit test for the permissions table
"""

# Import from internal modules
from cornflow.endpoints import PermissionsViewRoleEndpoint
from cornflow.shared.const import ROLES_MAP
from cornflow.tests.const import PERMISSION_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestPermissionsViewRoleEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.roles_with_access = PermissionsViewRoleEndpoint.ROLES_WITH_ACCESS

    def tearDown(self):
        super().tearDown()

    def test_get_permissions_view_role(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)

            response = self.client.get(
                PERMISSION_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )

            self.assertEqual(200, response.status_code)

    def test_get_no_permissions_view_role(self):
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    PERMISSION_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )

                self.assertEqual(403, response.status_code)
