"""
Unit tests for the get_resources function
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from cornflow.endpoints import get_resources, resources
from cornflow.shared.const import CONDITIONAL_ENDPOINTS


class TestGetResources(unittest.TestCase):
    """Test the get_resources function"""

    def setUp(self):
        self.app = Flask(__name__)
        self.mock_signup_view = MagicMock()
        self.mock_signup_view.view_class = MagicMock()
        self.mock_login_view = MagicMock()
        self.mock_login_view.view_class = MagicMock()

    def test_returns_base_resources_when_no_conditional_endpoints(self):
        """Test that get_resources returns base resources when no conditional endpoints are registered"""
        with self.app.app_context():
            with patch("flask.current_app.view_functions", {}):
                result = get_resources()
                self.assertEqual(result, resources)

    def test_adds_conditional_endpoint_when_registered(self):
        """Test that get_resources adds conditional endpoints when they are registered"""
        with self.app.app_context():
            mock_view_functions = {"signup": self.mock_signup_view}

            with patch("flask.current_app.view_functions", mock_view_functions):
                result = get_resources()

                # Should have one more resource than base
                self.assertEqual(len(result), len(resources) + 1)

                # Check that signup endpoint was added correctly
                signup_resource = next(
                    (r for r in result if r["endpoint"] == "signup"), None
                )
                self.assertIsNotNone(signup_resource)
                self.assertEqual(
                    signup_resource["urls"], CONDITIONAL_ENDPOINTS["signup"]
                )
                self.assertEqual(
                    signup_resource["resource"], self.mock_signup_view.view_class
                )

    def test_adds_both_signup_and_login_when_registered(self):
        """Test that get_resources adds both signup and login when both are registered"""
        with self.app.app_context():
            mock_view_functions = {
                "signup": self.mock_signup_view,
                "login": self.mock_login_view,
            }

            with patch("flask.current_app.view_functions", mock_view_functions):
                result = get_resources()

                # Should have two more resources than base
                self.assertEqual(len(result), len(resources) + 2)

                # Check that both endpoints were added correctly
                signup_resource = next(
                    (r for r in result if r["endpoint"] == "signup"), None
                )
                login_resource = next(
                    (r for r in result if r["endpoint"] == "login"), None
                )

                self.assertIsNotNone(signup_resource)
                self.assertIsNotNone(login_resource)
                self.assertEqual(
                    signup_resource["urls"], CONDITIONAL_ENDPOINTS["signup"]
                )
                self.assertEqual(login_resource["urls"], CONDITIONAL_ENDPOINTS["login"])

    def test_does_not_add_duplicate_endpoints(self):
        """Test that get_resources does not add endpoints that already exist in base resources"""
        with self.app.app_context():
            mock_view_functions = {
                "instance": MagicMock()
            }  # 'instance' already exists in base resources

            with patch("flask.current_app.view_functions", mock_view_functions):
                result = get_resources()
                self.assertEqual(len(result), len(resources))

    def test_ignores_non_conditional_endpoints(self):
        """Test that get_resources ignores endpoints that are not in CONDITIONAL_ENDPOINTS"""
        with self.app.app_context():
            mock_view_functions = {"non_conditional_endpoint": MagicMock()}

            with patch("flask.current_app.view_functions", mock_view_functions):
                result = get_resources()
                self.assertEqual(len(result), len(resources))


if __name__ == "__main__":
    unittest.main()
