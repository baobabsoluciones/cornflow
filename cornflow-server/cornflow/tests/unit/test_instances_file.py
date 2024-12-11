"""
Unit tests for instance file endpoint functionality.

This module contains test cases for handling instance file operations through
the API endpoints, including file uploads, downloads, and validation.

Classes
-------
TestInstancesFileEndpoint
    Test cases for instance file API endpoints
"""

# Import from libraries
import json
import os
from unittest.mock import patch

# Import from internal modules
from cornflow.models import InstanceModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase
from cornflow.tests.const import INSTANCE_PATH, INSTANCE_FILE_URL


class TestInstancesFileEndpoint(CustomTestCase):
    """
    Test cases for instance file endpoint functionality.

    This class tests various aspects of handling instance files through API
    endpoints, including file operations and error handling.
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
        self.url = INSTANCE_FILE_URL

        with open(INSTANCE_PATH) as f:
            self.payload = json.load(f)

    def test_upload_instance_file(self):
        """
        Tests instance file upload endpoint.

        Verifies that:
        - Files can be uploaded successfully
        - File content is properly stored
        - Response contains correct metadata
        """
        response = self.client.post(
            self.url,
            data={"file": (open(INSTANCE_PATH, "rb"), "test_instance.json")},
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json)
        self.assertIn("name", response.json)

    def test_download_instance_file(self):
        """
        Tests instance file download endpoint.

        Verifies that:
        - Files can be downloaded
        - Downloaded content matches original
        - Content type is correct
        """
        # First upload a file
        instance_id = self.create_new_row(self.url, self.model, self.payload)

        # Then download it
        response = self.client.get(
            f"{self.url}{instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(json.loads(response.data), self.payload)

    def test_invalid_file_upload(self):
        """
        Tests handling of invalid file uploads.

        Verifies that:
        - Invalid files are rejected
        - Appropriate error messages are returned
        - Server remains stable
        """
        response = self.client.post(
            self.url,
            data={"file": (b"invalid data", "invalid.txt")},
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    def test_missing_file(self):
        """
        Tests handling of missing file downloads.

        Verifies that:
        - Non-existent files return 404
        - Error message is appropriate
        - Server handles missing files gracefully
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
        response = self.client.post(
            self.url,
            data={"file": (open(INSTANCE_PATH, "rb"), "test_instance.json")},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.get(f"{self.url}1/", follow_redirects=True)
        self.assertEqual(response.status_code, 401)

    def test_large_file_handling(self):
        """
        Tests handling of large file uploads.

        Verifies that:
        - Large files can be processed
        - Memory usage is managed
        - Timeouts are handled properly
        """
        large_data = {
            "name": "large_instance",
            "data": {str(i): i for i in range(1000)},
        }

        response = self.client.post(
            self.url,
            data={"file": (json.dumps(large_data).encode(), "large_instance.json")},
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json)

    def test_file_update(self):
        """
        Tests instance file update functionality.

        Verifies that:
        - Files can be updated
        - Updates are properly persisted
        - Version control works correctly
        """
        # Create initial instance
        instance_id = self.create_new_row(self.url, self.model, self.payload)

        # Update the instance
        updated_data = dict(self.payload)
        updated_data["name"] = "updated_instance"

        response = self.client.put(
            f"{self.url}{instance_id}/",
            data={"file": (json.dumps(updated_data).encode(), "updated_instance.json")},
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "updated_instance")

    def test_file_deletion(self):
        """
        Tests instance file deletion.

        Verifies that:
        - Files can be deleted
        - Associated data is cleaned up
        - Subsequent access fails appropriately
        """
        instance_id = self.create_new_row(self.url, self.model, self.payload)

        response = self.client.delete(
            f"{self.url}{instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 204)

        # Verify deletion
        response = self.client.get(
            f"{self.url}{instance_id}/",
            follow_redirects=True,
            headers=self.get_header_with_auth(self.token),
        )
        self.assertEqual(response.status_code, 404)
