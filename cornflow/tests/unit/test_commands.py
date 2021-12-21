from flask_testing import TestCase

from cornflow.app import (
    create_app,
    create_service_user,
    create_admin_user,
    register_actions,
    access_init,
    register_roles,
    register_views,
    register_deployed_dags,
)

from cornflow.commands.dag import register_deployed_dags_command_test

from cornflow.endpoints import resources
from cornflow.models import (
    ActionModel,
    ApiViewModel,
    DeployedDAG,
    PermissionViewRoleModel,
    RoleModel,
    UserModel,
)
from cornflow.shared.const import (
    ACTIONS_MAP,
    ROLES_MAP,
    BASE_PERMISSION_ASSIGNATION,
)
from cornflow.shared.utils import db


class TestCommands(TestCase):
    def create_app(self):
        app = create_app("testing")
        return app

    def setUp(self):
        db.create_all()
        self.payload = {
            "email": "testemail@test.org",
            "password": "Testpassword1!",
        }
        self.resources = resources
        self.runner = create_app().test_cli_runner()
        self.runner.invoke(register_roles, ["-v", 1])

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_service_user_command(self):
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
        return user

    def test_service_user_existing_admin(self):
        self.test_admin_user_command()
        self.runner.invoke(
            create_service_user,
            [
                "-u",
                "administrator",
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        self.assertEqual("administrator", user.username)
        # TODO: check the user has both roles

    def test_service_user_existing_service(self):
        self.test_service_user_command()
        user = self.test_service_user_command()

        self.assertEqual("cornflow", user.username)
        # TODO: check the user has the role

    #
    def test_admin_user_command(self):
        self.runner.invoke(
            create_admin_user,
            [
                "-u",
                "administrator",
                "-e",
                self.payload["email"],
                "-p",
                self.payload["password"],
            ],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        return user

    def test_register_actions(self):
        self.runner.invoke(register_actions)

        actions = ActionModel.query.all()

        for a in actions:
            self.assertEqual(ACTIONS_MAP[a.id], a.name)

    def test_register_views(self):
        self.runner.invoke(register_views)

        views = ApiViewModel.query.all()
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
                        base[0],
                        ApiViewModel.query.filter_by(name=view["endpoint"]).first().id,
                        base[1],
                    )

                    self.assertEqual(True, permission)

    def test_deployed_dags_test_command(self):
        register_deployed_dags_command_test()
        dags = DeployedDAG.get_all_objects()
        for dag in ["solve_model_dag", "gc", "timer"]:
            self.assertIn(dag, [d.id for d in dags])

    # def test_argument_parsing_correct(self):
    #     command = RegisterRoles()
    #     command.run(verbose="0")
    #
    #     roles = RoleModel.query.all()
    #
    #     for r in roles:
    #         self.assertEqual(ROLES_MAP[r.id], r.name)
