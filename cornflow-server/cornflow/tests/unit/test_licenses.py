from cornflow.endpoints import LicensesEndpoint
from cornflow.tests.const import LICENSES_URL, _get_file
from cornflow.tests.custom_test_case import CustomTestCase


class TestLicensesListEndpoint(CustomTestCase):
    @staticmethod
    def read_requirements():
        with open(_get_file("../../requirements.txt")) as req:
            content = req.read()
            requirements = content.split("\n")

        requirements = [
            r.split("=")[0].split(">")[0].split("<")[0].split("@")[0].lower()
            for r in requirements
            if r != "" and not r.startswith("#")
        ]
        return requirements

    def setUp(self):
        super().setUp()
        self.roles_with_access = LicensesEndpoint.ROLES_WITH_ACCESS
        self.libraries = self.read_requirements()

    def tearDown(self):
        super().tearDown()

    def test_get_licenses(self):
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                LICENSES_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )

            self.assertEqual(200, response.status_code)
            self.assertIsInstance(response.json, list)
            libraries = [k["library"].lower() for k in response.json]

            for lib in self.libraries:
                self.assertIn(lib, libraries)
