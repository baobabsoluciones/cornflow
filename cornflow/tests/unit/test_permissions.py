"""
Unit test for the permissions table
"""
import json

# Import from internal modules
from cornflow.app import create_app
from cornflow.endpoints import PermissionsViewRoleEndpoint
from cornflow.models import InstanceModel
from cornflow.shared.const import ROLES_MAP
from cornflow.tests.const import INSTANCE_PATH, INSTANCE_URL, PERMISSION_URL
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


class TestPermissionsDagNoOpen(CustomTestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = 0
        return app

    def setUp(self):
        super().setUp()
        self.url = INSTANCE_URL
        self.model = InstanceModel

        def load_file(_file):
            with open(_file) as f:
                temp = json.load(f)
            return temp

        self.payload = load_file(INSTANCE_PATH)

    def test_create_instance_no_permissions(self):
        self.create_new_row(self.url, self.model, self.payload, 403, False)

    def test_missing_schema(self):
        self.payload.pop("schema")
        self.create_new_row(self.url, self.model, self.payload, 400, False)
