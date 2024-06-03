"""
Unit test for the version endpoint
"""

# Import from internal modules
from cornflow.endpoints import VersionEndpoint

from cornflow.tests.const import VERSION_URL
from cornflow.tests.custom_test_case import CustomTestCase

from cornflow.__version__ import VERSION
from importlib.metadata import version


class TestVersionEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = VERSION_URL
        self.roles_with_access = VersionEndpoint.ROLES_WITH_ACCESS
        self.items_to_check = {
            "cornflow_version": VERSION,
            "airflow_version": version("apache-airflow"),
        }

    def tearDown(self):
        super().tearDown()

    def test_get_version(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                self.url,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(self.items_to_check, response.json)
