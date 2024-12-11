"""
Unit test for database table functionality.

This module contains test cases for database table operations, ensuring proper
table creation, modification, and relationship handling.

Classes
-------
TestTables
    Test cases for database table operations and relationships
"""

# Import from libraries
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.models import UserModel, InstanceModel, CaseModel
from cornflow.shared import db


class TestTables(TestCase):
    """
    Test cases for database table operations.

    This class tests the database table functionality, including table creation,
    relationships between models, and data integrity constraints.
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

        Initializes the database and creates test data including:
        - Database tables
        - Test users
        - Test instances
        - Test cases
        """
        db.create_all()
        self.user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpassword1!",
            }
        )
        self.user.save()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Removes all database tables and session data.
        """
        db.session.remove()
        db.drop_all()

    def test_user_creation(self):
        """
        Tests user model creation and retrieval.

        Verifies that:
        - Users can be created with valid data
        - User attributes are correctly stored
        - Users can be retrieved from the database
        """
        user = UserModel.query.filter_by(username="testuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@test.com")

    def test_instance_creation(self):
        """
        Tests instance model creation and user relationship.

        Verifies that:
        - Instances can be created with valid data
        - Instance-user relationships are properly established
        - Instance attributes are correctly stored
        """
        instance = InstanceModel(
            data={
                "name": "test_instance",
                "description": "Test instance description",
                "data": {"test": "data"},
                "user_id": self.user.id,
            }
        )
        instance.save()

        retrieved_instance = InstanceModel.query.filter_by(name="test_instance").first()
        self.assertIsNotNone(retrieved_instance)
        self.assertEqual(retrieved_instance.user_id, self.user.id)
        self.assertEqual(retrieved_instance.description, "Test instance description")

    def test_case_creation(self):
        """
        Tests case model creation and relationships.

        Verifies that:
        - Cases can be created with valid data
        - Case-user relationships are properly established
        - Case-instance relationships are correctly handled
        """
        instance = InstanceModel(
            data={
                "name": "test_instance",
                "data": {"test": "data"},
                "user_id": self.user.id,
            }
        )
        instance.save()

        case = CaseModel(
            data={
                "name": "test_case",
                "description": "Test case description",
                "instance_id": instance.id,
                "user_id": self.user.id,
            }
        )
        case.save()

        retrieved_case = CaseModel.query.filter_by(name="test_case").first()
        self.assertIsNotNone(retrieved_case)
        self.assertEqual(retrieved_case.user_id, self.user.id)
        self.assertEqual(retrieved_case.instance_id, instance.id)

    def test_cascade_delete(self):
        """
        Tests cascade deletion functionality.

        Verifies that:
        - Deleting a parent record cascades to related records
        - Related records are properly deleted
        - Database integrity is maintained
        """
        instance = InstanceModel(
            data={
                "name": "test_instance",
                "data": {"test": "data"},
                "user_id": self.user.id,
            }
        )
        instance.save()

        case = CaseModel(
            data={
                "name": "test_case",
                "instance_id": instance.id,
                "user_id": self.user.id,
            }
        )
        case.save()

        instance.delete()

        self.assertIsNone(InstanceModel.query.get(instance.id))
        self.assertIsNone(CaseModel.query.get(case.id))

    def test_relationship_constraints(self):
        """
        Tests database relationship constraints.

        Verifies that:
        - Foreign key constraints are enforced
        - Invalid relationships are prevented
        - Relationship integrity is maintained
        """
        # Try to create instance with non-existent user
        instance = InstanceModel(
            data={
                "name": "test_instance",
                "data": {"test": "data"},
                "user_id": 9999,  # Non-existent user ID
            }
        )

        try:
            instance.save()
            db.session.commit()
            self.fail("Should have raised an integrity error")
        except:
            db.session.rollback()
            self.assertIsNone(
                InstanceModel.query.filter_by(name="test_instance").first()
            )
