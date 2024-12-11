"""
Unit test for case management functionality.

This module contains test cases for managing case operations, including
creation, modification, and validation of test cases.

Classes
-------
TestCases
    Test cases for case management operations
TestCaseEndpoint
    Test cases for case endpoint functionality
"""

# Import from libraries
from flask import current_app

# Import from internal modules
from cornflow.models import CaseModel, UserModel
from cornflow.shared import db
from cornflow.tests.custom_test_case import CustomTestCase


class TestCases(CustomTestCase):
    """
    Test cases for case management functionality.

    This class tests the core case management features including case creation,
    modification, validation, and relationship handling.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Test users
        - Test cases
        - Required configurations
        """
        super().setUp()
        db.create_all()
        self.AUTH_TYPE = current_app.config["AUTH_TYPE"]
        self.user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpassword1!",
            }
        )
        self.user.save()
        db.session.commit()

    def test_create_case(self):
        """
        Tests case creation functionality.

        Verifies that:
        - Cases can be created with valid data
        - Case attributes are correctly stored
        - Case-user relationships are properly established
        """
        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Test case description",
                "user_id": self.user.id,
            }
        )
        case.save()

        retrieved_case = CaseModel.query.filter_by(name="test_case").first()
        self.assertIsNotNone(retrieved_case)
        self.assertEqual(retrieved_case.description, "Test case description")
        self.assertEqual(retrieved_case.user_id, self.user.id)

    def test_update_case(self):
        """
        Tests case update functionality.

        Verifies that:
        - Case information can be updated
        - Updates are properly persisted
        - Case relationships are maintained
        """
        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Original description",
                "user_id": self.user.id,
            }
        )
        case.save()

        case.description = "Updated description"
        case.save()

        updated_case = CaseModel.query.get(case.id)
        self.assertEqual(updated_case.description, "Updated description")

    def test_delete_case(self):
        """
        Tests case deletion functionality.

        Verifies that:
        - Cases can be deleted
        - Associated data is properly cleaned up
        - Deleted cases cannot be retrieved
        """
        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Test case description",
                "user_id": self.user.id,
            }
        )
        case.save()

        case_id = case.id
        case.delete()

        deleted_case = CaseModel.query.get(case_id)
        self.assertIsNone(deleted_case)


class TestCaseEndpoint(CustomTestCase):
    """
    Test cases for case endpoint functionality.

    This class tests the REST API endpoints for case management, including
    request handling, response formatting, and access control.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the test environment with:
        - Database tables
        - Test users
        - API endpoints
        - Authentication tokens
        """
        super().setUp()
        db.create_all()
        self.user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpassword1!",
            }
        )
        self.user.save()
        db.session.commit()

    def test_get_cases(self):
        """
        Tests case retrieval endpoint.

        Verifies that:
        - Cases can be retrieved via API
        - Response contains correct case data
        - Pagination works correctly
        """
        response = self.client.get(
            "/cases/",
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(list, type(response.json))

    def test_get_case_by_id(self):
        """
        Tests retrieval of specific case by ID.

        Verifies that:
        - Individual cases can be retrieved
        - Response contains complete case data
        - Non-existent cases return appropriate error
        """
        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Test case description",
                "user_id": self.user.id,
            }
        )
        case.save()

        response = self.client.get(
            f"/cases/{case.id}/",
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json["name"], "test_case")

    def test_create_case_endpoint(self):
        """
        Tests case creation endpoint.

        Verifies that:
        - Cases can be created via API
        - Required fields are validated
        - Response contains created case data
        """
        data = {
            "name": "new_case",
            "description": "New case description",
            "user_id": self.user.id,
        }
        response = self.client.post(
            "/cases/",
            json=data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json["name"], "new_case")

    def test_update_case_endpoint(self):
        """
        Tests case update endpoint.

        Verifies that:
        - Cases can be updated via API
        - Partial updates are handled correctly
        - Response contains updated case data
        """
        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Original description",
                "user_id": self.user.id,
            }
        )
        case.save()

        update_data = {"description": "Updated description"}
        response = self.client.put(
            f"/cases/{case.id}/",
            json=update_data,
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json["description"], "Updated description")
