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
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE
from cornflow.models import DeployedDAG, PermissionsDAG, UserModel, UserRoleModel
from cornflow.shared.const import EXEC_STATE_CORRECT, EXEC_STATE_MANUAL
from cornflow.shared import db
from cornflow.tests.const import (
    CASE_PATH,
    DAG_URL,
    DEPLOYED_DAG_URL,
    EXECUTION_URL_NORUN,
    INSTANCE_URL,
    LOGIN_URL,
    SIGNUP_URL,
    USER_URL,
)
from cornflow.tests.unit.test_executions import TestExecutionsDetailEndpointMock
from cornflow_client import get_pulp_jsonschema, get_empty_schema


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

    def test_get_no_dag(self):
        idx = self.create_new_row(EXECUTION_URL_NORUN, self.model, self.payload)
        data = self.get_one_row(
            url=DAG_URL + idx + "/",
            token=self.token,
            check_payload=False,
            payload=self.payload,
            expected_status=403,
        )


class TestDeployedDAG(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        register_deployed_dags_command_test(verbose=False)
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

        data = dict(self.admin)
        data.pop("email")
        self.admin["id"] = response.json["id"]

        self.token = self.client.post(
            LOGIN_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        user_role = UserRoleModel({"user_id": self.admin["id"], "role_id": ADMIN_ROLE})
        user_role.save()
        db.session.commit()

        user_role = UserRoleModel(
            {"user_id": self.admin["id"], "role_id": SERVICE_ROLE}
        )
        user_role.save()
        db.session.commit()

        register_dag_permissions_command(verbose=False)

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

    def test_get_deployed_dags(self):
        response = self.client.get(
            DEPLOYED_DAG_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json[0],
            {
                "description": None,
                "id": "solve_model_dag",
                "instance_schema": get_pulp_jsonschema(),
                "solution_schema": get_pulp_jsonschema(),
                "config_schema": get_empty_schema(solvers=["cbc", "PULP_CBC_CMD"]),
                "instance_checks_schema": {},
                "solution_checks_schema": {},
            },
        )
        self.assertEqual(response.json[1]["id"], "gc")
        self.assertEqual(response.json[2]["id"], "timer")

    def test_endpoint_permissions(self):
        user_role = UserRoleModel.query.filter_by(
            user_id=self.admin["id"], role_id=SERVICE_ROLE
        )
        user_role.delete()
        db.session.commit()
        data = self.client.get(
            DEPLOYED_DAG_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(data.status_code, 403)
        self.assertEqual(
            data.json, {"error": "You do not have permission to access this endpoint"}
        )

    def test_post_endpoint(self):
        payload = {
            "description": None,
            "id": "test_dag",
            "instance_schema": {},
            "solution_schema": {},
            "instance_checks_schema": {},
            "solution_checks_schema": {},
            "config_schema": {},
        }
        response = self.client.post(
            DEPLOYED_DAG_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, payload)

        response = self.client.get(
            DEPLOYED_DAG_URL,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(payload, response.json)

    def test_post_not_valid(self):
        payload = {"description": "test_description"}
        response = self.client.post(
            DEPLOYED_DAG_URL,
            data=json.dumps(payload),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "'id': ['Missing data for required field.']",
            response.json.get("error", ""),
        )
