"""
Unit test for the DAG endpoints
"""

# Import from libraries
import json
from flask_testing import TestCase

# Import from internal modules
from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.shared.const import ADMIN_ROLE
from cornflow.models import DeployedDAG, PermissionsDAG, UserModel, UserRoleModel
from cornflow.shared.const import EXEC_STATE_CORRECT, EXEC_STATE_MANUAL
from cornflow.shared.utils import db
from cornflow.tests.const import (
    CASE_PATH,
    DAG_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_URL,
    SIGNUP_URL,
    USER_URL,
)
from cornflow.tests.unit.test_executions import TestExecutionsDetailEndpointMock


class TestDagEndpoint(TestExecutionsDetailEndpointMock):
    def test_manual_dag_service_user(self):
        with open(CASE_PATH) as f:
            payload = json.load(f)
        data = dict(
            data=payload["data"],
            state=EXEC_STATE_MANUAL,
        )
        payload_to_send = {**self.payload, **data}
        token = self.create_service_user()

        self.items_to_check = [
            "config",
            "name",
            "description",
            "schema",
            "instance_id",
            "state",
        ]

        idx = self.create_new_row(
            url=DAG_URL,
            model=self.model,
            payload=payload_to_send,
            check_payload=True,
            token=token,
        )

    def test_manual_dag_planner_user(self):
        with open(CASE_PATH) as f:
            payload = json.load(f)
        data = dict(
            data=payload["data"],
            state=EXEC_STATE_MANUAL,
        )
        payload_to_send = {**self.payload, **data}
        token = self.create_planner()

        self.items_to_check = [
            "config",
            "name",
            "description",
            "schema",
            "instance_id",
            "state",
        ]

        idx = self.create_new_row(
            url=DAG_URL,
            model=self.model,
            payload=payload_to_send,
            check_payload=True,
            token=token,
        )


class TestDagDetailEndpoint(TestExecutionsDetailEndpointMock):
    def test_put_dag(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        with open(CASE_PATH) as f:
            payload = json.load(f)
        data = dict(
            data=payload["data"],
            state=EXEC_STATE_CORRECT,
        )
        payload_to_check = {**self.payload, **data}
        token = self.create_service_user()
        data = self.update_row(
            url=DAG_URL + idx + "/",
            payload_to_check=payload_to_check,
            change=data,
            token=token,
            check_payload=False,
        )

    def test_get_dag(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        token = self.create_service_user()
        data = self.get_one_row(
            url=DAG_URL + idx + "/",
            token=token,
            check_payload=False,
            payload=self.payload,
        )
        instance_data = self.get_one_row(
            url=INSTANCE_URL + self.payload["instance_id"] + "/data/",
            payload=dict(),
            check_payload=False,
        )
        self.assertEqual(data["data"], instance_data["data"])
        self.assertEqual(data["config"], self.payload["config"])
        return


class TestDeployedDAGModel(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(0)
        register_deployed_dags_command_test(verbose=0)
        self.url = USER_URL
        self.model = UserModel
        self.admin = dict(
            username="anAdminUser", email="admin@admin.com", password="Testpassword1!"
        )

        response = self.client.post(
            SIGNUP_URL,
            data=json.dumps(self.admin),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        )

        self.admin["id"] = response.json["id"]

        user_role = UserRoleModel({"user_id": self.admin["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        register_dag_permissions_command(verbose=0)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_permission_cascade_deletion(self):
        before = PermissionsDAG.get_user_dag_permissions(self.admin["id"])
        self.assertIsNotNone(before)
        dag = DeployedDAG.query.get("solve_model_dag")
        dag.delete()
        after = PermissionsDAG.get_user_dag_permissions(self.admin["id"])
        self.assertNotEqual(before, after)
        self.assertGreater(len(before), len(after))
