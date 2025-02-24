"""
Unit tests for the API views endpoint.

This module contains tests for the API views endpoint functionality, including:
- Authorization checks for different user roles
- Validation of API view listings
- Access control verification for endpoints

Classes
-------
TestApiViewListEndpoint
    Tests for the API views list endpoint functionality
"""

# Import from internal modules
from cornflow.endpoints import ApiViewListEndpoint, resources
from cornflow.models import ViewModel
from cornflow.shared.const import ROLES_MAP
from cornflow.tests.const import APIVIEW_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestApiViewListEndpoint(CustomTestCase):
    """
    Test cases for the API views list endpoint.

    This class tests the functionality of listing available API views, including:
    - Authorization checks for different user roles
    - Validation of returned API view data
    - Access control for authorized and unauthorized roles
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes test data including:
        - Base test case setup
        - Roles with access permissions
        - Test payload with API view data
        - Items to check in responses
        """
        super().setUp()
        self.roles_with_access = ApiViewListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
            for view in resources
        ]
        self.items_to_check = ["name", "description", "url_rule"]

    def tearDown(self):
        """Clean up test environment after each test."""
        super().tearDown()

    def test_get_api_view_authorized(self):
        """
        Test that authorized roles can access the API views list.

        Verifies that users with proper roles can:
        - Successfully access the API views endpoint
        - Receive the correct list of views
        - Get properly formatted view data with all required fields
        """
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                APIVIEW_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            for item in range(len(self.payload)):
                for field in self.items_to_check:
                    self.assertEqual(
                        self.payload[item][field], response.json[item][field]
                    )

    def test_get_api_view_not_authorized(self):
        """
        Test that unauthorized roles cannot access the API views list.

        Verifies that users without proper roles:
        - Are denied access to the API views endpoint
        - Receive appropriate error responses with 403 status code
        """
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    APIVIEW_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )

                self.assertEqual(403, response.status_code)


class TestApiViewModel(CustomTestCase):
    """
    Test cases for the API views list endpoint.

    This class tests the functionality of listing available API views, including:
    - Authorization checks for different user roles
    - Validation of returned API view data
    - Access control for authorized and unauthorized roles
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes test data including:
        - Base test case setup
        - Roles with access permissions
        - Test payload with API view data
        - Items to check in responses
        """
        super().setUp()
        self.roles_with_access = ApiViewListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
            for view in resources
        ]
        self.items_to_check = ["name", "description", "url_rule"]

    def test_get_all_objects(self):
        """
        Test that the get_all_objects method works properly
        """
        objective = len(resources) + 2

        instances = ViewModel.get_all_objects().all()
        self.assertEqual(len(instances), objective)

        instances = ViewModel.get_all_objects(offset=10, limit=10).all()
        self.assertEqual(len(instances), 10)

        instances = ViewModel.get_all_objects(offset=10).all()
        self.assertEqual(len(instances), objective - 10)

        instances = ViewModel.get_all_objects(limit=10).all()
        self.assertEqual(len(instances), 10)

    def test_get_one_object_by_name(self):
        """
        Test that the get_one_by_name method works properly
        """
        instance = ViewModel.get_one_by_name(name="instance")
        self.assertEqual(instance.name, "instance")

    def test_get_one_object(self):
        """
        Test that the get_one_object method works properly
        """
        instance = ViewModel.get_one_object(idx=1)
        self.assertEqual(instance.name, "instance")

    def test_get_one_object_without_idx(self):
        """
        Test that the get_one_object method works properly
        """
        instance = ViewModel.get_one_object(name="instance")
        self.assertEqual(instance.name, "instance")
