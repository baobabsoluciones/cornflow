import json


from cornflow.models import UserRoleModel
from cornflow.shared.const import ADMIN_ROLE, SUPER_ADMIN_ROLE
from cornflow.tests.const import LOGIN_URL, PERMISSION_URL, SIGNUP_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestPermissionsViewRoleEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_permissions_view_role(self):
        token = self.create_super_admin()
        response = self.client.get(
            PERMISSION_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )

        self.assertEqual(200, response.status_code)

    def test_get_no_permissions_view_role(self):
        response = self.client.get(
            PERMISSION_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(403, response.status_code)
