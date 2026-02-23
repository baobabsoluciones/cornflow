import re

from cornflow.endpoints import LicensesEndpoint
from cornflow.tests.const import LICENSES_URL, _get_file
from cornflow.tests.custom_test_case import CustomTestCase


def _parse_dependency_name(spec):
    spec = spec.split(";")[0].strip().strip('"')
    return re.split(r"\[|==|>=|<=|>|<|~=|!=", spec)[0].lower()


class TestLicensesListEndpoint(CustomTestCase):
    @staticmethod
    def read_requirements():
        pyproject_path = _get_file("../../../pyproject.toml")
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        deps = data.get("project", {}).get("dependencies", [])
        return [_parse_dependency_name(d) for d in deps]

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
