import json

from flask_testing import TestCase

from cornflow.app import (
    access_init,
    create_admin_user,
    create_app,
    create_base_user,
    create_service_user,
    register_actions,
    register_dag_permissions,
    register_roles,
    register_views,
)
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.endpoints import resources, alarms_resources
from cornflow.models import (
    ActionModel,
    PermissionViewRoleModel,
    RoleModel,
    ViewModel,
)
from cornflow.models import (
    DeployedDAG,
    PermissionsDAG,
    UserModel,
)
from cornflow.shared import db
from cornflow.shared.const import (
    ACTIONS_MAP,
    ROLES_MAP,
    BASE_PERMISSION_ASSIGNATION,
)
from cornflow.tests.const import LOGIN_URL, INSTANCE_URL, INSTANCE_PATH
from cornflow.tests.integration.test_cornflowclient import load_file


class TestCommands(TestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = 1
        return app

    def setUp(self):
        db.create_all()
        self.payload = {
            "email": "testemail@test.org",
            "password": "Testpassword1!",
        }
        self.resources = resources + alarms_resources
        self.runner = self.create_app().test_cli_runner()
        self.runner.invoke(register_roles, ["-v"])

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def user_command(self, command, username, email):
        self.runner.invoke(
            command,
            ["-u", username, "-e", email, "-p", self.payload["password"], "-v"],
        )

        user = UserModel.get_one_user_by_email(email)

        self.assertNotEqual(None, user)
        self.assertEqual(email, user.email)
        return user

    def user_missing_arguments(self, command):
        result = self.runner.invoke(
            command,
            [
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-u' / '--username'", result.output)

        result = self.runner.invoke(
            command,
            [
                "-u",
                "cornflow",
                "-p",
                self.payload["password"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-e' / '--email'", result.output)

        result = self.runner.invoke(
            command,
            [
                "-u",
                "cornflow",
                "-e",
                self.payload["email"],
            ],
        )
        self.assertEqual(2, result.exit_code)
        self.assertIn("Missing option '-p' / '--password'", result.output)

    def test_service_user_command(self):
        return self.user_command(create_service_user, "cornflow", self.payload["email"])

    def test_service_user_existing_admin(self):
        self.test_admin_user_command()
        self.runner.invoke(
            create_service_user,
            [
                "-u",
                "cornflow",
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        self.assertEqual("cornflow", user.username)
        # TODO: check the user has both roles

    def test_service_user_existing_service(self):
        self.test_service_user_command()
        user = self.test_service_user_command()

        self.assertEqual("cornflow", user.username)
        # TODO: check the user has the role

    def test_admin_user_command(self):
        return self.user_command(create_admin_user, "admin", "admin@test.org")

    def test_base_user_command(self):
        return self.user_command(create_base_user, "base", "base@test.org")

    def test_register_actions(self):
        self.runner.invoke(register_actions)

        actions = ActionModel.query.all()

        for a in actions:
            self.assertEqual(ACTIONS_MAP[a.id], a.name)

    def test_register_views(self):
        self.runner.invoke(register_views)

        views = ViewModel.query.all()
        views_list = [v.name for v in views]
        resources_list = [
            self.resources[i]["endpoint"] for i in range(len(self.resources))
        ]

        self.assertCountEqual(views_list, resources_list)

    def test_register_roles(self):
        roles = RoleModel.query.all()
        for r in roles:
            self.assertEqual(ROLES_MAP[r.id], r.name)

    def test_base_permissions_assignation(self):
        self.runner.invoke(access_init)

        for base in BASE_PERMISSION_ASSIGNATION:
            for view in self.resources:
                if base[0] in view["resource"].ROLES_WITH_ACCESS:
                    permission = PermissionViewRoleModel.get_permission(
                        role_id=base[0],
                        api_view_id=ViewModel.query.filter_by(name=view["endpoint"])
                        .first()
                        .id,
                        action_id=base[1],
                    )

                    self.assertEqual(True, permission)

    def test_deployed_dags_test_command(self):
        register_deployed_dags_command_test(verbose=True)
        dags = DeployedDAG.get_all_objects()
        for dag in ["solve_model_dag", "gc", "timer"]:
            self.assertIn(dag, [d.id for d in dags])

    def test_dag_permissions_command(self):
        register_deployed_dags_command_test()
        self.test_service_user_command()
        self.test_admin_user_command()
        self.runner.invoke(register_dag_permissions, ["-o", 1])

        service = UserModel.get_one_user_by_email("testemail@test.org")
        admin = UserModel.get_one_user_by_email("admin@test.org")

        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        admin_permissions = PermissionsDAG.get_user_dag_permissions(admin.id)

        self.assertEqual(3, len(service_permissions))
        self.assertEqual(3, len(admin_permissions))

    def test_dag_permissions_command_no_open(self):
        register_deployed_dags_command_test()
        self.test_service_user_command()
        self.test_admin_user_command()
        self.runner.invoke(register_dag_permissions, ["-o", 0])

        service = UserModel.get_one_user_by_email("testemail@test.org")
        admin = UserModel.get_one_user_by_email("admin@test.org")

        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        admin_permissions = PermissionsDAG.get_user_dag_permissions(admin.id)

        self.assertEqual(3, len(service_permissions))
        self.assertEqual(0, len(admin_permissions))

    def test_argument_parsing_correct(self):
        self.test_service_user_command()
        result = self.runner.invoke(register_dag_permissions, ["-o", "a"])

        self.assertEqual(2, result.exit_code)
        self.assertIn("is not a valid integer", result.output)

        service = UserModel.get_one_user_by_email("testemail@test.org")
        service_permissions = PermissionsDAG.get_user_dag_permissions(service.id)
        self.assertEqual(0, len(service_permissions))

    def test_argument_parsing_incorrect(self):
        self.test_service_user_command()
        result = self.runner.invoke(register_dag_permissions, ["-o", "a"])
        self.assertEqual(2, result.exit_code)
        self.assertIn("is not a valid integer", result.output)

    def test_missing_required_argument_service(self):
        self.user_missing_arguments(create_service_user)

    def test_missing_required_argument_admin(self):
        self.user_missing_arguments(create_admin_user)

    def test_missing_required_argument_user(self):
        self.user_missing_arguments(create_base_user)

    def test_error_no_views(self):
        self.test_service_user_command()
        token = self.client.post(
            LOGIN_URL,
            data=json.dumps(
                {"username": "cornflow", "password": self.payload["password"]}
            ),
            follow_redirects=True,
            headers={"Content-Type": "application/json"},
        ).json["token"]

        data = load_file(INSTANCE_PATH)
        response = self.client.post(
            INSTANCE_URL,
            data=json.dumps(data),
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        self.assertEqual(403, response.status_code)
