"""

"""
from cornflow.shared.const import BASE_ROLES
from cornflow.tests.const import ROLES_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestRolesListEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_roles_super_admin(self):
        token = self.create_super_admin()
        response = self.client.get(
            ROLES_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(200, response.status_code)
        roles_list = [{"id": key, "name": value} for key, value in BASE_ROLES.items()]
        self.assertCountEqual(roles_list, response.json)

    def test_get_roles_admin(self):
        token = self.create_admin()
        response = self.client.get(
            ROLES_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(200, response.status_code)
        roles_list = [{"id": key, "name": value} for key, value in BASE_ROLES.items()]
        self.assertCountEqual(roles_list, response.json)

    def test_get_no_roles(self):
        response = self.client.get(
            ROLES_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(403, response.status_code)
