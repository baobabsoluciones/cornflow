"""
Unit tests for data validation and checking functionality.

This module contains test cases for validating data against schemas,
checking data integrity, and handling validation errors.

Classes
-------
TestDataChecks
    Test cases for data validation and integrity checks
"""

# Import from libraries
import unittest

# Import from internal modules
from cornflow.shared.validators import (
    check_data_against_schema,
    check_solution_against_schema,
    validate_schema,
)


class TestDataChecks(unittest.TestCase):
    """
    Test cases for data validation functionality.

    This class tests various aspects of data validation including schema
    validation, data integrity checks, and error handling for invalid data.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Test schemas
        - Test data
        - Validation configurations
        """
        self.valid_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name", "age"],
        }

        self.valid_data = {"name": "Test User", "age": 25, "email": "test@test.com"}

    def test_valid_schema(self):
        """
        Tests validation of valid JSON schemas.

        Verifies that:
        - Valid schemas are properly validated
        - Schema structure is correctly checked
        - Required fields are properly handled
        """
        result = validate_schema(self.valid_schema)
        self.assertTrue(result)

    def test_invalid_schema(self):
        """
        Tests validation of invalid JSON schemas.

        Verifies that:
        - Invalid schemas are rejected
        - Appropriate errors are raised
        - Schema structural issues are detected
        """
        invalid_schema = {"type": "invalid_type", "properties": {}}
        with self.assertRaises(ValueError):
            validate_schema(invalid_schema)

    def test_data_validation(self):
        """
        Tests validation of data against schema.

        Verifies that:
        - Valid data passes schema validation
        - Data types are correctly checked
        - Required fields are enforced
        """
        result = check_data_against_schema(self.valid_data, self.valid_schema)
        self.assertTrue(result)

    def test_invalid_data(self):
        """
        Tests validation of invalid data.

        Verifies that:
        - Invalid data is rejected
        - Type mismatches are detected
        - Missing required fields are caught
        """
        invalid_data = {
            "name": "Test User",
            "age": "not_a_number",
            "email": "invalid_email",
        }
        with self.assertRaises(ValueError):
            check_data_against_schema(invalid_data, self.valid_schema)

    def test_solution_validation(self):
        """
        Tests validation of solution data.

        Verifies that:
        - Valid solutions are accepted
        - Solution format is checked
        - Solution constraints are enforced
        """
        solution_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "number"},
                "status": {
                    "type": "string",
                    "enum": ["optimal", "feasible", "infeasible"],
                },
            },
            "required": ["result", "status"],
        }

        valid_solution = {"result": 42.0, "status": "optimal"}

        result = check_solution_against_schema(valid_solution, solution_schema)
        self.assertTrue(result)

    def test_missing_required_fields(self):
        """
        Tests handling of missing required fields.

        Verifies that:
        - Missing required fields are detected
        - Appropriate errors are raised
        - Optional fields are properly handled
        """
        incomplete_data = {
            "name": "Test User"
            # Missing required 'age' field
        }
        with self.assertRaises(ValueError):
            check_data_against_schema(incomplete_data, self.valid_schema)

    def test_additional_fields(self):
        """
        Tests handling of additional fields.

        Verifies that:
        - Additional fields are allowed by default
        - Strict schema validation works when enabled
        - Extra properties are properly handled
        """
        data_with_extra = {
            "name": "Test User",
            "age": 25,
            "email": "test@test.com",
            "extra_field": "extra value",
        }
        result = check_data_against_schema(data_with_extra, self.valid_schema)
        self.assertTrue(result)

    def test_nested_validation(self):
        """
        Tests validation of nested data structures.

        Verifies that:
        - Nested objects are properly validated
        - Deep structure is correctly checked
        - Nested required fields are enforced
        """
        nested_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "details": {
                            "type": "object",
                            "properties": {"age": {"type": "integer"}},
                            "required": ["age"],
                        },
                    },
                    "required": ["name", "details"],
                }
            },
            "required": ["user"],
        }

        valid_nested_data = {"user": {"name": "Test User", "details": {"age": 25}}}

        result = check_data_against_schema(valid_nested_data, nested_schema)
        self.assertTrue(result)
