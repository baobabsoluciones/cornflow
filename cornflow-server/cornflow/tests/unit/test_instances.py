"""
Unit tests for instance management functionality.

This module contains test cases for managing instances, including creation,
modification, querying, and deletion of problem instances.

Classes
-------
TestInstances
    Test cases for instance management operations
TestInstanceDetailEndpoint
    Test cases for instance detail endpoints
"""

# Import from libraries
import json
from unittest.mock import patch

# Import from internal modules
from cornflow.models import InstanceModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import INSTANCE_PATH, INSTANCE_URL


class TestInstances(CustomTestCase):
    """
    Test cases for instance management functionality.

    This class tests various aspects of managing problem instances including
    creation, modification, and basic operations.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Database tables
        - Test data
        - API endpoints
        - Authentication tokens
        """
        super().setUp()
        self.model = InstanceModel
        self.url = INSTANCE_URL

        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    def test_create_instance(self):
        """
        Tests instance creation.

        Verifies that:
        - Instances can be created with valid data
        - Response contains correct metadata
        - Instance data is properly stored
        """
        response = self.create_new_row(self.url, self.model, self.payload)
        self.assertIsNotNone(response)
        instance = self.model.query.get(response)
        self.assertEqual(instance.data, self.payload["data"])

    def test_list_instances(self):
        """
        Tests instance listing functionality.

        Verifies that:
        - All instances can be retrieved
        - List contains correct metadata
        - Pagination works correctly
        """
        # Create multiple instances
        for i in range(3):
            data = dict(self.payload)
            data["name"] = f"instance_{i}"
            self.create_new_row(self.url, self.model, data)

        response = self.client.get(
            self.url,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)

    def test_invalid_instance(self):
        """
        Tests handling of invalid instance data.

        Verifies that:
        - Invalid data is rejected
        - Appropriate error messages are returned
        - Database integrity is maintained
        """
        invalid_data = dict(self.payload)
        invalid_data["data"] = "invalid"  # Should be a dict

        response = self.client.post(
            self.url,
            json=invalid_data,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 400)


class TestInstanceDetailEndpoint(CustomTestCase):
    """
    Test cases for instance detail endpoint functionality.

    This class tests the detailed operations on individual instances
    including retrieval, updates, and deletion.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Database tables
        - Test instance
        - API endpoints
        - Authentication tokens
        """
        super().setUp()
        self.model = InstanceModel
        self.url = INSTANCE_URL

        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

        self.instance_id = self.create_new_row(self.url, self.model, self.payload)

    def test_get_instance(self):
        """
        Tests instance retrieval.

        Verifies that:
        - Individual instances can be retrieved
        - Response contains complete data
        - Access control works correctly
        """
        response = self.client.get(
            f"{self.url}{self.instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"], self.payload["data"])

    def test_update_instance(self):
        """
        Tests instance update functionality.

        Verifies that:
        - Instances can be updated
        - Updates are properly persisted
        - Response reflects changes
        """
        updated_data = dict(self.payload)
        updated_data["name"] = "updated_name"

        response = self.client.put(
            f"{self.url}{self.instance_id}/",
            json=updated_data,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "updated_name")

    def test_delete_instance(self):
        """
        Tests instance deletion.

        Verifies that:
        - Instances can be deleted
        - Associated data is cleaned up
        - Subsequent access fails appropriately
        """
        response = self.client.delete(
            f"{self.url}{self.instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 204)

        # Verify deletion
        response = self.client.get(
            f"{self.url}{self.instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 404)

    def test_instance_not_found(self):
        """
        Tests handling of non-existent instances.

        Verifies that:
        - Non-existent instances return 404
        - Error message is appropriate
        - Server handles missing data gracefully
        """
        response = self.client.get(
            f"{self.url}999/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json)

    def test_unauthorized_access(self):
        """
        Tests unauthorized access attempts.

        Verifies that:
        - Unauthorized requests are rejected
        - Authentication is properly enforced
        - Security headers are present
        """
        # Try without authentication
        response = self.client.get(
            f"{self.url}{self.instance_id}/", follow_redirects=True
        )
        self.assertEqual(response.status_code, 401)

        # Try with invalid token
        response = self.client.get(
            f"{self.url}{self.instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth("invalid_token"),
        )
        self.assertEqual(response.status_code, 401)

    def test_partial_update(self):
        """
        Tests partial instance updates.

        Verifies that:
        - Partial updates work correctly
        - Unmodified fields remain unchanged
        - Response contains updated data
        """
        partial_update = {"name": "partially_updated"}

        response = self.client.patch(
            f"{self.url}{self.instance_id}/",
            json=partial_update,
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "partially_updated")
        self.assertEqual(response.json["data"], self.payload["data"])
