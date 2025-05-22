import os

from cornflow.shared import db

from cornflow.app import create_app
from cornflow.commands import access_init_command
from cornflow.shared.const import STATUS_HEALTHY, CORNFLOW_VERSION
from cornflow.tests.const import HEALTH_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestHealth(CustomTestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_health(self):
        self.create_service_user()
        os.environ["CORNFLOW_SERVICE_USER"] = "testuser4"
        response = self.client.get(HEALTH_URL)
        self.assertEqual(200, response.status_code)
        cf_status = response.json["cornflow_status"]
        af_status = response.json["airflow_status"]
        cf_version = response.json["cornflow_version"]
        expected_version = CORNFLOW_VERSION
        self.assertEqual(str, type(cf_status))
        self.assertEqual(str, type(af_status))
        self.assertEqual(cf_status, STATUS_HEALTHY)
        self.assertEqual(cf_version, expected_version)
