import os
from unittest.mock import patch, MagicMock

from cornflow.shared import db

from cornflow.app import create_app
from cornflow.commands import access_init_command
from cornflow.shared.const import (
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    CORNFLOW_VERSION,
    DATABRICKS_BACKEND,
    AIRFLOW_BACKEND,
)
from cornflow.shared.exceptions import EndpointNotImplemented
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
        backend_status = response.json["backend_status"]
        cf_version = response.json["cornflow_version"]
        expected_version = CORNFLOW_VERSION
        self.assertEqual(str, type(cf_status))
        self.assertEqual(str, type(backend_status))
        self.assertEqual(cf_status, STATUS_HEALTHY)
        self.assertEqual(cf_version, expected_version)

    @patch("cornflow.endpoints.health.Databricks")
    def test_health_databricks_backend_healthy(self, mock_databricks):
        """Test health endpoint with Databricks backend when service is healthy"""
        self.create_service_user()
        os.environ["CORNFLOW_SERVICE_USER"] = "testuser4"

        # Mock Databricks client
        mock_db_client = MagicMock()
        mock_db_client.is_alive.return_value = True
        mock_databricks.from_config.return_value = mock_db_client

        # Set Databricks backend
        with self.app.app_context():
            self.app.config["CORNFLOW_BACKEND"] = DATABRICKS_BACKEND

            response = self.client.get(HEALTH_URL)

            self.assertEqual(200, response.status_code)
            cf_status = response.json["cornflow_status"]
            backend_status = response.json["backend_status"]
            cf_version = response.json["cornflow_version"]

            self.assertEqual(cf_status, STATUS_HEALTHY)
            self.assertEqual(backend_status, STATUS_HEALTHY)
            self.assertEqual(cf_version, CORNFLOW_VERSION)

            # Verify Databricks client was called
            mock_databricks.from_config.assert_called_once()
            mock_db_client.is_alive.assert_called_once()

    @patch("cornflow.endpoints.health.Databricks")
    def test_health_databricks_backend_unhealthy(self, mock_databricks):
        """Test health endpoint with Databricks backend when service is unhealthy"""
        self.create_service_user()
        os.environ["CORNFLOW_SERVICE_USER"] = "testuser4"

        # Mock Databricks client
        mock_db_client = MagicMock()
        mock_db_client.is_alive.return_value = False
        mock_databricks.from_config.return_value = mock_db_client

        # Set Databricks backend
        with self.app.app_context():
            self.app.config["CORNFLOW_BACKEND"] = DATABRICKS_BACKEND

            response = self.client.get(HEALTH_URL)

            self.assertEqual(200, response.status_code)
            cf_status = response.json["cornflow_status"]
            backend_status = response.json["backend_status"]

            self.assertEqual(cf_status, STATUS_HEALTHY)
            self.assertEqual(backend_status, STATUS_UNHEALTHY)

            # Verify Databricks client was called
            mock_databricks.from_config.assert_called_once()
            mock_db_client.is_alive.assert_called_once()

    def test_health_unsupported_backend(self):
        """Test health endpoint with unsupported backend raises EndpointNotImplemented"""
        self.create_service_user()
        os.environ["CORNFLOW_SERVICE_USER"] = "testuser4"

        # Set an unsupported backend value
        with self.app.app_context():
            self.app.config["CORNFLOW_BACKEND"] = 999  # Invalid backend value

            response = self.client.get(HEALTH_URL)

            self.assertEqual(501, response.status_code)
            self.assertIn("error", response.json)
            self.assertEqual(response.json["error"], "Endpoint not implemented")
