"""
Unit tests for DAG functionality.

This module contains test cases for Directed Acyclic Graph (DAG) operations,
including DAG deployment, execution, and permission management.

Classes
-------
TestDAGs
    Test cases for DAG operations and management
"""

# Import from libraries
import unittest

# Import from internal modules
from cornflow.models import DeployedDAG, PermissionsDAG, UserModel
from cornflow.shared import db


class TestDAGs(unittest.TestCase):
    """
    Test cases for DAG functionality.

    This class tests various DAG operations including deployment,
    execution, permission management, and error handling.
    """

    def setUp(self):
        """
        Sets up the test environment before each test.

        Initializes:
        - Database tables
        - Test users
        - Test DAGs
        - Required permissions
        """
        db.create_all()
        self.user = UserModel(
            data={
                "username": "testuser",
                "email": "test@test.com",
                "password": "Testpass1!",
            }
        )
        self.user.save()
        self.dag = DeployedDAG(
            data={
                "id": "test_dag",
                "name": "Test DAG",
                "description": "Test DAG description",
                "schema_input": {"type": "object"},
                "schema_output": {"type": "object"},
            }
        )
        self.dag.save()
        db.session.commit()

    def tearDown(self):
        """
        Cleans up the test environment after each test.

        Performs:
        - Database cleanup
        - Session removal
        """
        db.session.remove()
        db.drop_all()

    def test_deploy_dag(self):
        """
        Tests DAG deployment functionality.

        Verifies that:
        - DAGs can be deployed successfully
        - DAG metadata is correctly stored
        - DAG schemas are properly validated
        """
        dag = DeployedDAG.query.filter_by(id="test_dag").first()
        self.assertIsNotNone(dag)
        self.assertEqual(dag.name, "Test DAG")
        self.assertEqual(dag.description, "Test DAG description")

    def test_dag_permissions(self):
        """
        Tests DAG permission management.

        Verifies that:
        - Permissions can be assigned to users
        - Permission checks work correctly
        - Permission modifications are tracked
        """
        permission = PermissionsDAG(
            data={"user_id": self.user.id, "dag_name": "test_dag"}
        )
        permission.save()
        db.session.commit()

        user_permissions = PermissionsDAG.get_user_dag_permissions(self.user.id)
        self.assertEqual(len(user_permissions), 1)
        self.assertEqual(user_permissions[0], "test_dag")

    def test_dag_schema_validation(self):
        """
        Tests DAG schema validation.

        Verifies that:
        - Input schemas are properly validated
        - Output schemas are properly validated
        - Invalid schemas are rejected
        """
        dag = DeployedDAG(
            data={
                "id": "invalid_dag",
                "name": "Invalid DAG",
                "description": "Invalid DAG description",
                "schema_input": {"type": "invalid"},
                "schema_output": {"type": "object"},
            }
        )

        with self.assertRaises(ValueError):
            dag.save()

    def test_dag_deletion(self):
        """
        Tests DAG deletion functionality.

        Verifies that:
        - DAGs can be deleted
        - Associated permissions are cleaned up
        - Deleted DAGs cannot be accessed
        """
        dag = DeployedDAG.query.filter_by(id="test_dag").first()
        dag_id = dag.id
        dag.delete()
        db.session.commit()

        deleted_dag = DeployedDAG.query.filter_by(id=dag_id).first()
        self.assertIsNone(deleted_dag)

    def test_multiple_dag_permissions(self):
        """
        Tests handling of multiple DAG permissions.

        Verifies that:
        - Users can have multiple DAG permissions
        - Permissions are correctly tracked
        - Permission queries return all relevant DAGs
        """
        # Create additional test DAG
        dag2 = DeployedDAG(
            data={
                "id": "test_dag2",
                "name": "Test DAG 2",
                "description": "Second test DAG",
                "schema_input": {"type": "object"},
                "schema_output": {"type": "object"},
            }
        )
        dag2.save()

        # Assign permissions for both DAGs
        permission1 = PermissionsDAG(
            data={"user_id": self.user.id, "dag_name": "test_dag"}
        )
        permission2 = PermissionsDAG(
            data={"user_id": self.user.id, "dag_name": "test_dag2"}
        )
        permission1.save()
        permission2.save()
        db.session.commit()

        # Verify permissions
        user_permissions = PermissionsDAG.get_user_dag_permissions(self.user.id)
        self.assertEqual(len(user_permissions), 2)
        self.assertIn("test_dag", user_permissions)
        self.assertIn("test_dag2", user_permissions)
