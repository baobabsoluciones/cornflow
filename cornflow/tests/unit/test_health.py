from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.shared.utils import db
from cornflow.tests.const import HEALTH_URL
from cornflow.shared.const import STATUS_HEALTHY, STATUS_UNHEALTHY


class TestLogIn(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_health(self):
        response = self.client.get(HEALTH_URL)
        self.assertEqual(200, response.status_code)
        cf_status = response.json["cornflow_status"]
        af_status = response.json["airflow_status"]
        self.assertEqual(str, type(cf_status))
        self.assertEqual(str, type(af_status))
        self.assertEqual(cf_status, STATUS_HEALTHY)
