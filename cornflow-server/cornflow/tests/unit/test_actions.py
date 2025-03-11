"""
Unit tests for the actions endpoint.

This module contains tests for the actions API endpoint functionality, including:
- Authorization checks for different user roles
- Validation of action listings
- Access control verification

Classes
-------
TestActionsListEndpoint
    Tests for the actions list endpoint functionality
"""

# Import from libraries
from cornflow.endpoints import ActionListEndpoint
from cornflow.shared.const import ACTIONS_MAP, ROLES_MAP
from cornflow.tests.const import ACTIONS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestActionsListEndpoint(CustomTestCase):
    """
    Test cases for the actions list endpoint.

    This class tests the functionality of listing available actions, including:
    - Authorization checks for different user roles
    - Validation of returned action data
    - Access control for authorized and unauthorized roles
    """

    def setUp(self):
        """
        Set up test environment before each test.

        Initializes test data including:
        - Base test case setup
        - Roles with access permissions
        - Test payload with action data
        """
        super().setUp()
        self.roles_with_access = ActionListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {"id": key, "name": value.replace("_", " ")}
            for key, value in ACTIONS_MAP.items()
        ]

    def tearDown(self):
        """
        Clean up test environment after each test.
        """
        super().tearDown()

    def test_get_actions_authorized(self):
        """
        Test that authorized roles can access the actions list.

        Verifies that users with proper roles can:
        - Successfully access the actions endpoint
        - Receive the correct list of actions
        - Get properly formatted action data
        """
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                ACTIONS_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertCountEqual(self.payload, response.json)

    def test_get_actions_not_authorized(self):
        """
        Test that unauthorized roles cannot access the actions list.

        Verifies that users without proper roles:
        - Are denied access to the actions endpoint
        - Receive appropriate error responses
        """
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    ACTIONS_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                )

                self.assertEqual(403, response.status_code)
