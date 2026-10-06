"""
Unit tests for the common rule that creates the DAG permissions
(PermissionsDAG.add_missing_dag_permissions).
"""

from datetime import datetime, timezone
from unittest.mock import patch

from flask_testing import TestCase
from sqlalchemy.exc import DBAPIError

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.models import PermissionsDAG, UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, PLANNER_ROLE, SERVICE_ROLE

ALL_DAGS = ["solve_model_dag", "gc", "timer", "979073949072767"]
PRIVILEGED = ["service_user", "admin1", "admin2"]


class TestAddMissingDagPermissions(TestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = "0"
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test()
        self.users = {}
        self.create_user("service_user", [SERVICE_ROLE])
        self.create_user("admin1", [ADMIN_ROLE])
        self.create_user("admin2", [ADMIN_ROLE])
        self.create_user("planner1", [PLANNER_ROLE])

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user(self, username, roles):
        user = UserModel(
            {
                "username": username,
                "email": f"{username}@test.org",
                "password": "Testpassword1!",
            }
        )
        user.save()
        for role in roles:
            UserRoleModel({"user_id": user.id, "role_id": role}).save()
        self.users[username] = user.id
        return user.id

    def pairs(self):
        return {(p.dag_id, p.user_id) for p in PermissionsDAG.query.all()}

    def expected(self, dags, usernames):
        return {(dag, self.users[name]) for dag in dags for name in usernames}

    def test_open_deployment_all_users(self):
        created = PermissionsDAG.add_missing_dag_permissions(ALL_DAGS, 1)
        self.assertEqual(16, len(created))
        self.assertEqual(self.expected(ALL_DAGS, self.users.keys()), self.pairs())

        PermissionsDAG.query.delete()
        db.session.commit()
        PermissionsDAG.add_missing_dag_permissions(["gc"], 1)
        self.assertEqual({"gc"}, {dag for dag, _ in self.pairs()})
        self.assertEqual(4, PermissionsDAG.query.count())

    def test_closed_deployment_admins_and_service(self):
        PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(self.expected(["gc"], PRIVILEGED), self.pairs())
        self.assertEqual(
            0, PermissionsDAG.query.filter_by(user_id=self.users["planner1"]).count()
        )

    def test_closed_deployment_user_with_several_roles(self):
        multi_admin = self.create_user("multi_admin", [PLANNER_ROLE, ADMIN_ROLE])
        multi_service = self.create_user("multi_service", [PLANNER_ROLE, SERVICE_ROLE])
        both = self.create_user("both", [ADMIN_ROLE, SERVICE_ROLE])
        PermissionsDAG.add_missing_dag_permissions(ALL_DAGS, 0)
        for user_id in (multi_admin, multi_service, both):
            self.assertEqual(4, PermissionsDAG.query.filter_by(user_id=user_id).count())

    def test_closed_deployment_disabled_admin_role(self):
        user_id = self.create_user("admin_disabled", [ADMIN_ROLE])
        user_role = UserRoleModel.query.filter_by(user_id=user_id).first()
        user_role.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(0, PermissionsDAG.query.filter_by(user_id=user_id).count())
        self.assertEqual(self.expected(["gc"], PRIVILEGED), self.pairs())

    def test_open_deployment_as_string(self):
        self.app.config["OPEN_DEPLOYMENT"] = "1"
        PermissionsDAG.add_missing_dag_permissions(ALL_DAGS)
        self.assertEqual(16, PermissionsDAG.query.count())

        PermissionsDAG.query.delete()
        db.session.commit()
        self.app.config["OPEN_DEPLOYMENT"] = "0"
        PermissionsDAG.add_missing_dag_permissions(ALL_DAGS)
        self.assertEqual(self.expected(ALL_DAGS, PRIVILEGED), self.pairs())

        PermissionsDAG.query.delete()
        db.session.commit()
        PermissionsDAG.add_missing_dag_permissions(["gc"], "0")
        self.assertEqual(self.expected(["gc"], PRIVILEGED), self.pairs())

    def test_idempotent(self):
        existing = PermissionsDAG({"dag_id": "gc", "user_id": self.users["service_user"]})
        existing.save()
        existing_id = existing.id

        created = PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(
            {self.users["admin1"], self.users["admin2"]},
            {p.user_id for p in created},
        )
        self.assertEqual(self.expected(["gc"], PRIVILEGED), self.pairs())
        row = PermissionsDAG.query.filter_by(
            dag_id="gc", user_id=self.users["service_user"]
        ).one()
        self.assertEqual(existing_id, row.id)

        before = PermissionsDAG.query.count()
        self.assertEqual([], PermissionsDAG.add_missing_dag_permissions(["gc"], 0))
        self.assertEqual(before, PermissionsDAG.query.count())

    def test_existing_soft_deleted_row_not_duplicated(self):
        existing = PermissionsDAG({"dag_id": "gc", "user_id": self.users["service_user"]})
        existing.save()
        existing.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        created = PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(
            {self.users["admin1"], self.users["admin2"]},
            {p.user_id for p in created},
        )
        self.assertEqual(
            1,
            PermissionsDAG.query.filter_by(
                dag_id="gc", user_id=self.users["service_user"]
            ).count(),
        )

    def test_db_error_rollback_and_reraise(self):
        with patch.object(
            db.session, "commit", side_effect=DBAPIError("stmt", {}, Exception("forced"))
        ):
            with self.assertRaises(DBAPIError):
                PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(0, PermissionsDAG.query.count())
        created = PermissionsDAG.add_missing_dag_permissions(["gc"], 0)
        self.assertEqual(3, len(created))
        self.assertEqual(3, PermissionsDAG.query.count())
