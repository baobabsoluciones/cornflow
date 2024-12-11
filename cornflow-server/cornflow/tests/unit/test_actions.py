"""
Unit test for the actions endpoint.

This module contains test cases for the actions endpoint, which handles
the listing and authorization of different actions in the system.

Classes
-------
TestActionsListEndpoint
    Test cases for the actions list endpoint functionality
"""

# Import from libraries
from cornflow.endpoints import ActionListEndpoint
from cornflow.shared.const import ACTIONS_MAP, ROLES_MAP
from cornflow.tests.const import ACTIONS_URL
from cornflow.tests.custom_test_case import CustomTestCase


class TestActionsListEndpoint(CustomTestCase):
    """
    Test cases for the actions list endpoint functionality.

    This class tests the authorization and retrieval of actions for different user roles.
    It verifies that only users with appropriate roles can access the actions list.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the roles with access and creates a payload of actions
        from the ACTIONS_MAP constant.
        """
        super().setUp()
        self.roles_with_access = ActionListEndpoint.ROLES_WITH_ACCESS
        self.payload = [
            {"id": key, "name": value.replace("_", " ")}
            for key, value in ACTIONS_MAP.items()
        ]

    def tearDown(self):
        """
        Cleans up the test environment after each test.
        """
        super().tearDown()

    def test_get_actions_authorized(self):
        """
        Tests that authorized roles can access the actions list.

        Verifies that users with roles that have access can retrieve
        the complete list of actions and receive a 200 status code.
        """
        for role in self.roles_with_access:
            self.token = self.create_user_with_role(role)
            response = self.client.get(
                ACTIONS_URL,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.token,
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertCountEqual(self.payload, response.json)

    def test_get_actions_not_authorized(self):
        """
        Tests that unauthorized roles cannot access the actions list.

        Verifies that users with roles that don't have access receive
        a 403 forbidden status code when attempting to retrieve the actions list.
        """
        for role in ROLES_MAP:
            if role not in self.roles_with_access:
                self.token = self.create_user_with_role(role)
                response = self.client.get(
                    ACTIONS_URL,
                    follow_redirects=True,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                    },
                )

                self.assertEqual(403, response.status_code)
