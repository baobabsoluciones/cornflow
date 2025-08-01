"""
Unit tests for validators module
"""

import json

from unittest import TestCase
from unittest.mock import patch

from cornflow.tests.const import SPECIAL_CHARACTERS_PATH, PASSWORD_PATTERN_PATH
from cornflow.shared.validators import (
    is_special_character,
    check_password_pattern,
    check_email_pattern,
    extend_with_default,
    json_schema_validate,
    json_schema_extend_and_validate,
    json_schema_validate_as_string,
    json_schema_extend_and_validate_as_string,
)


class TestIsSpecialCharacter(TestCase):
    """Test cases for is_special_character function"""

    def test_special_characters_battery(self):
        """
        Data-driven test for is_special_character using JSON test cases.
        """
        with open(SPECIAL_CHARACTERS_PATH, encoding="utf-8") as f:
            test_cases = json.load(f)

        for case in test_cases:
            input_value = case["input"]
            expected = case["expected"]
            check = case["check"]
            error_message = case["error_message"]
            # If input_value is a list, iterate through it and subtest each element
            if isinstance(input_value, list):
                for val in input_value:
                    with self.subTest(input=val, expected=expected, check=check):
                        try:
                            result = is_special_character(val)
                            if check == "equals":
                                self.assertEqual(
                                    result, expected, error_message + f" (input: {val})"
                                )
                            else:
                                self.fail(f"Unknown check type: {check}")
                        except TypeError:
                            self.assertFalse(
                                expected,
                                error_message + f" (TypeError raised, input: {val})",
                            )
            else:
                with self.subTest(input=input_value, expected=expected, check=check):
                    try:
                        result = is_special_character(input_value)
                        if check == "equals":
                            self.assertEqual(result, expected, error_message)
                        else:
                            self.fail(f"Unknown check type: {check}")
                    except TypeError:
                        self.assertFalse(
                            expected, error_message + " (TypeError raised)"
                        )


class TestCheckPasswordPattern(TestCase):
    """Test cases for check_password_pattern function"""

    def test_data_driven_from_json(self):
        """
        Data-driven test for check_password_pattern using JSON test cases.
        """

        with open(PASSWORD_PATTERN_PATH, encoding="utf-8") as f:
            test_cases = json.load(f)

        for case in test_cases:
            input_value = case["input"]
            expected = case["expected"]
            check = case["check"]
            error_message = case["error_message"]
            with self.subTest(input=input_value, expected=expected, check=check):
                result = list(check_password_pattern(input_value))
                if check == "equals":
                    self.assertEqual(result, expected, error_message)
                else:
                    self.fail(f"Unknown check type: {check}")


class TestCheckEmailPattern(TestCase):
    """Test cases for check_email_pattern function"""

    def test_valid_emails(self):
        """Test that valid email addresses pass validation"""
        valid_emails = [
            "user@example.com",
            "test.user@domain.org",
            "user123@test-domain.co.uk",
            "user_name@example-domain.com",
            "user+tag@example.com",
        ]
        for email in valid_emails:
            with self.subTest(email=email):
                is_valid, error = check_email_pattern(email)
                self.assertTrue(is_valid)
                self.assertIsNone(error)

    def test_invalid_email_format(self):
        """Test that invalid email formats fail"""
        invalid_emails = [
            "invalid-email",
            "user@",
            "@domain.com",
            "user@domain",
            "user domain.com",
            "user@.com",
            "user@domain.",
        ]
        for email in invalid_emails:
            with self.subTest(email=email):
                is_valid, error = check_email_pattern(email)
                self.assertFalse(is_valid)
                self.assertEqual(error, "Invalid email address.")

    @patch("cornflow.shared.validators.blocklist")
    def test_disposable_email_domain(self, mock_blocklist):
        """Test that disposable email domains are rejected"""
        mock_blocklist.__contains__ = lambda x: x == "tempmail.com"

        is_valid, error = check_email_pattern("user@tempmail.com")
        self.assertFalse(is_valid)
        self.assertEqual(error, "Invalid email address")

    @patch("cornflow.shared.validators.blocklist")
    def test_valid_email_domain(self, mock_blocklist):
        """Test that valid email domains pass validation"""
        mock_blocklist.__contains__ = lambda x: False

        is_valid, error = check_email_pattern("user@example.com")
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class TestExtendWithDefault(TestCase):
    """Test cases for extend_with_default function"""

    def test_extend_with_default(self):
        """Test that the validator is properly extended with default functionality"""
        from jsonschema import Draft7Validator

        extended_validator = extend_with_default(Draft7Validator)

        # Test that the extended validator has the set_defaults functionality
        self.assertIsNotNone(extended_validator)
        self.assertTrue(hasattr(extended_validator, "VALIDATORS"))


class TestJsonSchemaValidate(TestCase):
    """Test cases for json_schema_validate function"""

    def test_valid_data(self):
        """Test that valid data passes validation"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"name": "John", "age": 30}

        errors = json_schema_validate(schema, data)
        self.assertEqual(errors, [])

    def test_invalid_data(self):
        """Test that invalid data returns errors"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"age": "not_an_integer"}

        errors = json_schema_validate(schema, data)
        self.assertGreater(len(errors), 0)

    def test_missing_required_field(self):
        """Test that missing required fields return errors"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"age": 30}

        errors = json_schema_validate(schema, data)
        self.assertGreater(len(errors), 0)

    def test_empty_data(self):
        """Test validation with empty data"""
        schema = {"type": "object"}
        data = {}

        errors = json_schema_validate(schema, data)
        self.assertEqual(errors, [])


class TestJsonSchemaExtendAndValidate(TestCase):
    """Test cases for json_schema_extend_and_validate function"""

    def test_valid_data_with_defaults(self):
        """Test that valid data with defaults is properly extended"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Unknown"},
                "age": {"type": "integer", "default": 0},
            },
        }
        data = {"name": "John"}

        extended_data, errors = json_schema_extend_and_validate(schema, data)

        self.assertEqual(errors, [])
        self.assertEqual(extended_data["name"], "John")
        self.assertEqual(extended_data["age"], 0)

    def test_invalid_data_with_defaults(self):
        """Test that invalid data returns errors even with defaults"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Unknown"},
                "age": {"type": "integer", "default": 0},
            },
        }
        data = {"age": "not_an_integer"}

        extended_data, errors = json_schema_extend_and_validate(schema, data)

        self.assertGreater(len(errors), 0)
        self.assertEqual(extended_data["name"], "Unknown")

    def test_empty_data_with_defaults(self):
        """Test that empty data gets extended with defaults"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Unknown"},
                "age": {"type": "integer", "default": 0},
            },
        }
        data = {}

        extended_data, errors = json_schema_extend_and_validate(schema, data)

        self.assertEqual(errors, [])
        self.assertEqual(extended_data["name"], "Unknown")
        self.assertEqual(extended_data["age"], 0)


class TestJsonSchemaValidateAsString(TestCase):
    """Test cases for json_schema_validate_as_string function"""

    def test_valid_data_returns_empty_list(self):
        """Test that valid data returns empty list of string errors"""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        data = {"name": "John"}

        errors = json_schema_validate_as_string(schema, data)
        self.assertEqual(errors, [])

    def test_invalid_data_returns_string_errors(self):
        """Test that invalid data returns list of string errors"""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }
        data = {"age": "not_an_integer"}

        errors = json_schema_validate_as_string(schema, data)

        self.assertGreater(len(errors), 0)
        for error in errors:
            self.assertIsInstance(error, str)


class TestJsonSchemaExtendAndValidateAsString(TestCase):
    """Test cases for json_schema_extend_and_validate_as_string function"""

    def test_valid_data_with_defaults_returns_string_errors(self):
        """Test that valid data with defaults returns empty list of string errors"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Unknown"},
                "age": {"type": "integer", "default": 0},
            },
        }
        data = {"name": "John"}

        extended_data, errors = json_schema_extend_and_validate_as_string(schema, data)

        self.assertEqual(errors, [])
        self.assertEqual(extended_data["name"], "John")
        self.assertEqual(extended_data["age"], 0)

    def test_invalid_data_returns_string_errors(self):
        """Test that invalid data returns list of string errors"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "Unknown"},
                "age": {"type": "integer", "default": 0},
            },
        }
        data = {"age": "not_an_integer"}

        extended_data, errors = json_schema_extend_and_validate_as_string(schema, data)

        self.assertGreater(len(errors), 0)
        for error in errors:
            self.assertIsInstance(error, str)
        self.assertEqual(extended_data["name"], "Unknown")
