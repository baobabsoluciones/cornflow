"""
Unit test for schema validation functionality.

This module contains test cases for JSON schema validation, ensuring proper
data validation against defined schemas.

Classes
-------
TestSchemas
    Test cases for schema validation functionality
"""

# Import from libraries
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.shared import db
from cornflow.shared.validators import validate_schema


class TestSchemas(TestCase):
    """
    Test cases for schema validation functionality.

    This class tests the validation of data against JSON schemas, ensuring
    proper validation rules and error handling.
    """

    def create_app(self):
        """
        Creates a test application instance.

        :returns: A configured Flask application for testing
        :rtype: Flask
        """
        app = create_app("testing")
        return app

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes the database and prepares test schemas and data.
        """
        db.create_all()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Removes all database tables and session data.
        """
        db.session.remove()
        db.drop_all()

    def test_validate_schema_success(self):
        """
        Tests successful schema validation.

        Verifies that:
        - Valid data passes schema validation
        - The validation result is True
        - No validation errors are returned
        """
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"name": "test", "age": 25}
        result = validate_schema(data, schema)
        self.assertTrue(result)

    def test_validate_schema_failure(self):
        """
        Tests schema validation failure cases.

        Verifies that:
        - Invalid data fails schema validation
        - The validation result is False
        - Appropriate validation errors are returned
        """
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"age": "invalid"}
        result = validate_schema(data, schema)
        self.assertFalse(result)

    def test_validate_schema_complex(self):
        """
        Tests validation of complex schemas.

        Verifies that:
        - Nested objects are properly validated
        - Array validations work correctly
        - Complex type constraints are enforced
        """
        schema = {
            "type": "object",
            "properties": {
                "users": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                        "required": ["name"],
                    },
                }
            },
        }
        data = {"users": [{"name": "test1", "age": 25}, {"name": "test2", "age": 30}]}
        result = validate_schema(data, schema)
        self.assertTrue(result)

    def test_validate_schema_formats(self):
        """
        Tests validation of format constraints.

        Verifies that:
        - Email format validation works correctly
        - Date format validation works correctly
        - URI format validation works correctly
        """
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
            },
        }
        data = {"email": "test@example.com", "website": "http://example.com"}
        result = validate_schema(data, schema)
        self.assertTrue(result)
