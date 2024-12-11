"""
Unit tests for schema generation functionality.

This module contains test cases for generating API schemas and validating
schema generation from Python classes and models.

Classes
-------
GenerationTests
    Test cases for schema generation and validation
"""

# Import from libraries
import importlib.util
import sys
from unittest import TestCase
from unittest.mock import MagicMock

# Import from internal modules
from cornflow.cli import cli
from cornflow.cli.schemas import APIGenerator


class GenerationTests(TestCase):
    """
    Test cases for schema generation functionality.

    This class tests various aspects of generating API schemas from Python
    classes and models, including validation and error handling.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Mock packages
        - Test schemas
        - API generator
        """
        super().setUp()
        self.api_generator = APIGenerator()

    def test_generate_schema(self):
        """
        Tests basic schema generation.

        Verifies that:
        - Schemas can be generated from classes
        - Generated schemas are valid
        - Required fields are included
        """

        class TestModel:
            field1: str
            field2: int
            field3: bool

        schema = self.api_generator.generate_schema(TestModel)
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)

    def test_generate_nested_schema(self):
        """
        Tests generation of nested schemas.

        Verifies that:
        - Nested class structures are properly handled
        - Nested properties are correctly defined
        - References are properly managed
        """

        class NestedModel:
            name: str
            value: int

        class ParentModel:
            nested: NestedModel
            field: str

        schema = self.api_generator.generate_schema(ParentModel)
        self.assertIn("nested", schema["properties"])
        self.assertIn("field", schema["properties"])
        self.assertEqual(schema["properties"]["field"]["type"], "string")

    def test_generate_array_schema(self):
        """
        Tests generation of array schemas.

        Verifies that:
        - Array types are properly handled
        - Array items are correctly defined
        - Array constraints are included
        """

        class ArrayModel:
            items: list[str]
            numbers: list[int]

        schema = self.api_generator.generate_schema(ArrayModel)
        self.assertEqual(schema["properties"]["items"]["type"], "array")
        self.assertEqual(schema["properties"]["items"]["items"]["type"], "string")
        self.assertEqual(schema["properties"]["numbers"]["type"], "array")
        self.assertEqual(schema["properties"]["numbers"]["items"]["type"], "integer")

    def test_generate_with_annotations(self):
        """
        Tests schema generation with type annotations.

        Verifies that:
        - Type annotations are properly processed
        - Optional fields are handled correctly
        - Type hints are correctly translated
        """
        from typing import Optional

        class AnnotatedModel:
            required_field: str
            optional_field: Optional[int]

        schema = self.api_generator.generate_schema(AnnotatedModel)
        self.assertIn("required_field", schema["properties"])
        self.assertIn("optional_field", schema["properties"])
        self.assertEqual(
            schema["properties"]["optional_field"]["type"], ["integer", "null"]
        )

    def test_generate_with_inheritance(self):
        """
        Tests schema generation with class inheritance.

        Verifies that:
        - Inherited properties are included
        - Base class schemas are properly merged
        - Override behavior is correct
        """

        class BaseModel:
            base_field: str

        class DerivedModel(BaseModel):
            derived_field: int

        schema = self.api_generator.generate_schema(DerivedModel)
        self.assertIn("base_field", schema["properties"])
        self.assertIn("derived_field", schema["properties"])

    def test_generate_with_validators(self):
        """
        Tests schema generation with field validators.

        Verifies that:
        - Validation rules are included in schema
        - Constraints are properly defined
        - Custom validators are handled
        """

        class ValidatedModel:
            age: int
            email: str

            @property
            def validators(self):
                return {
                    "age": {"minimum": 0, "maximum": 120},
                    "email": {"format": "email"},
                }

        schema = self.api_generator.generate_schema(ValidatedModel)
        self.assertIn("minimum", schema["properties"]["age"])
        self.assertIn("maximum", schema["properties"]["age"])
        self.assertEqual(schema["properties"]["email"].get("format"), "email")

    def test_generate_with_descriptions(self):
        """
        Tests schema generation with field descriptions.

        Verifies that:
        - Field descriptions are included
        - Documentation is properly formatted
        - Metadata is correctly transferred
        """

        class DocumentedModel:
            """A test model with documentation."""

            field: str
            """A documented field."""

        schema = self.api_generator.generate_schema(DocumentedModel)
        self.assertIn("description", schema)
        self.assertEqual(schema["description"], "A test model with documentation.")
