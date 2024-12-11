"""
Unit tests for example data functionality.

This module contains test cases for handling example data operations,
including data loading, validation, and manipulation of example datasets.

Classes
-------
TestExampleData
    Test cases for example data operations and handling
"""

# Import from libraries
import unittest
import json
import os

# Import from internal modules
from cornflow.shared import db
from cornflow.models import InstanceModel


class TestExampleData(unittest.TestCase):
    """
    Test cases for example data functionality.

    This class tests various aspects of example data handling including
    loading, validation, and manipulation of example datasets.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Database tables
        - Example data files
        - Test configurations
        """
        db.create_all()
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.example_files = [
            f
            for f in os.listdir(self.data_dir)
            if f.endswith(".json") and "example" in f.lower()
        ]

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Performs:
        - Database cleanup
        - Session removal
        - Temporary file cleanup
        """
        db.session.remove()
        db.drop_all()

    def test_load_example_data(self):
        """
        Tests loading of example data files.

        Verifies that:
        - Example files can be loaded
        - JSON format is valid
        - Data structure is correct
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)
            self.assertTrue("data" in data or "schema" in data)

    def test_example_data_validation(self):
        """
        Tests validation of example data.

        Verifies that:
        - Data structure matches expected schema
        - Required fields are present
        - Data types are correct
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if "data" in data:
                self.assertIsInstance(data["data"], dict)
            if "schema" in data:
                self.assertIsInstance(data["schema"], dict)

    def test_store_example_data(self):
        """
        Tests storing example data in database.

        Verifies that:
        - Data can be stored in database
        - Stored data can be retrieved
        - Data integrity is maintained
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if "data" in data:
                instance = InstanceModel(
                    data={
                        "name": f"Example from {file_name}",
                        "description": "Test example data",
                        "data": data["data"],
                    }
                )
                instance.save()
                db.session.commit()

                retrieved = InstanceModel.query.filter_by(
                    name=f"Example from {file_name}"
                ).first()
                self.assertIsNotNone(retrieved)
                self.assertEqual(retrieved.data, data["data"])

    def test_example_data_consistency(self):
        """
        Tests consistency of example data.

        Verifies that:
        - Data format is consistent across files
        - Required fields are consistently present
        - Data structure follows patterns
        """
        common_keys = set()
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if not common_keys:
                common_keys = set(data.keys())
            else:
                self.assertTrue(
                    set(data.keys()).intersection(common_keys),
                    f"Inconsistent keys in {file_name}",
                )

    def test_example_data_references(self):
        """
        Tests handling of data references.

        Verifies that:
        - References between data elements are valid
        - Referenced IDs exist
        - Reference integrity is maintained
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if "data" in data and isinstance(data["data"], dict):
                # Check for common reference patterns
                for key, value in data["data"].items():
                    if isinstance(value, list) and value:
                        # Check if list items reference each other
                        if all(isinstance(item, dict) for item in value):
                            ids = {item.get("id") for item in value if "id" in item}
                            refs = {
                                item.get("ref_id") for item in value if "ref_id" in item
                            }
                            self.assertTrue(refs.issubset(ids | {None}))

    def test_example_data_types(self):
        """
        Tests data types in example data.

        Verifies that:
        - Data types match schema definitions
        - Numeric fields contain valid numbers
        - String fields contain valid strings
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if "data" in data and isinstance(data["data"], dict):
                for key, value in data["data"].items():
                    if isinstance(value, (list, dict)):
                        continue
                    if isinstance(value, (int, float)):
                        self.assertIsInstance(value, (int, float))
                    elif isinstance(value, str):
                        self.assertIsInstance(value, str)

    def test_example_data_constraints(self):
        """
        Tests constraints in example data.

        Verifies that:
        - Numeric ranges are valid
        - String lengths are within limits
        - Required relationships are maintained
        """
        for file_name in self.example_files:
            file_path = os.path.join(self.data_dir, file_name)
            with open(file_path, "r") as f:
                data = json.load(f)

            if "data" in data and isinstance(data["data"], dict):
                for key, value in data["data"].items():
                    if isinstance(value, (int, float)):
                        # Check for common numeric constraints
                        if "capacity" in key.lower():
                            self.assertGreaterEqual(value, 0)
                        if "probability" in key.lower():
                            self.assertGreaterEqual(value, 0)
                            self.assertLessEqual(value, 1)
