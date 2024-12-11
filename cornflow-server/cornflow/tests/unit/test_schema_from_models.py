# """
# Unit test for schema generation from models.
#
# This module contains test cases for generating JSON schemas from database models,
# ensuring proper schema validation and consistency.
#
# Classes
# -------
# TestSchemaFromModels
#     Test cases for model-to-schema conversion functionality
# """
#
# # Import from libraries
# from flask_testing import TestCase
#
# # Import from internal modules
# from cornflow.app import create_app
# from cornflow.models import UserModel
# from cornflow.shared import db
# from cornflow.shared.schema_from_models import get_schema_from_model
#
#
# class TestSchemaFromModels(TestCase):
#     """
#     Test cases for generating schemas from database models.
#
#     This class tests the automatic generation of JSON schemas from SQLAlchemy models,
#     ensuring proper type mapping and validation rules.
#     """
#
#     def create_app(self):
#         """
#         Creates a test application instance.
#
#         :returns: A configured Flask application for testing
#         :rtype: Flask
#         """
#         app = create_app("testing")
#         return app
#
#     def setUp(self):
#         """
#         Sets up the test environment before each test.
#
#         Initializes the database and prepares test models for schema generation.
#         """
#         db.create_all()
#
#     def tearDown(self):
#         """
#         Cleans up the test environment after each test.
#
#         Removes all database tables and session data.
#         """
#         db.session.remove()
#         db.drop_all()
#
#     def test_get_schema_from_model(self):
#         """
#         Tests schema generation from a model.
#
#         Verifies that:
#         - The schema is correctly generated from the model
#         - Required fields are properly identified
#         - Field types are correctly mapped
#         - Schema structure matches expectations
#         """
#         schema = get_schema_from_model(UserModel)
#         self.assertEqual(dict, type(schema))
#         self.assertEqual("object", schema["type"])
#         self.assertIn("properties", schema)
#         self.assertIn("required", schema)
#
#     def test_schema_properties(self):
#         """
#         Tests the properties of generated schemas.
#
#         Verifies that:
#         - All model fields are present in the schema
#         - Property types are correctly defined
#         - Property constraints are properly set
#         """
#         schema = get_schema_from_model(UserModel)
#         properties = schema["properties"]
#         self.assertIn("username", properties)
#         self.assertIn("email", properties)
#         self.assertIn("password", properties)
#         self.assertEqual("string", properties["username"]["type"])
#         self.assertEqual("string", properties["email"]["type"])
#         self.assertEqual("string", properties["password"]["type"])
#
#     def test_schema_required_fields(self):
#         """
#         Tests required field definitions in generated schemas.
#
#         Verifies that:
#         - Required fields are correctly identified
#         - The required fields list contains all mandatory fields
#         - Optional fields are not marked as required
#         """
#         schema = get_schema_from_model(UserModel)
#         required = schema["required"]
#         self.assertIn("username", required)
#         self.assertIn("email", required)
#         self.assertIn("password", required)
#
#     def test_schema_field_constraints(self):
#         """
#         Tests field constraints in generated schemas.
#
#         Verifies that:
#         - Length constraints are properly set
#         - Format validators are correctly defined
#         - Custom validators are properly included
#         """
#         schema = get_schema_from_model(UserModel)
#         properties = schema["properties"]
#         self.assertIn("maxLength", properties["username"])
#         self.assertIn("maxLength", properties["email"])
#         self.assertIn("maxLength", properties["password"])
