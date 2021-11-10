from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands import (
    RegisterBasePermissions,
    CreateAdminUser,
    CreateServiceUser,
    RegisterActions,
    RegisterRoles,
    RegisterViews,
)
from cornflow.endpoints import resources
from cornflow.models import (
    ActionModel,
    ApiViewModel,
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
            "password": "testpassword",
        }
        self.resources = resources
        RegisterRoles().run(0)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_service_user_command(self):
        command = CreateServiceUser()

        command.run(
            username="cornflow",
            email=self.payload["email"],
            password=self.payload["password"],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        return user

    def test_service_user_existing_admin(self):
        self.test_admin_user_command()
        command = CreateServiceUser()

        command.run(
            username="administrator",
            email=self.payload["email"],
            password=self.payload["password"],
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

    def test_admin_user_command(self):
        command = CreateAdminUser()

        command.run(
            username="administrator",
            email=self.payload["email"],
            password=self.payload["password"],
        )

        user = UserModel.get_one_user_by_email("testemail@test.org")

        self.assertNotEqual(None, user)
        self.assertEqual(self.payload["email"], user.email)
        return user

    def test_register_actions(self):
        command = RegisterActions()
        command.run()

        actions = ActionModel.query.all()

        for a in actions:
            self.assertEqual(ACTIONS_MAP[a.id], a.name)

    def test_register_views(self):
        command = RegisterViews()
        command.run()

        views = ApiViewModel.query.all()
        views_list = [v.name for v in views]
        resources_list = [
            self.resources[i]["endpoint"] for i in range(len(self.resources))
        ]

        self.assertCountEqual(views_list, resources_list)

    def test_register_roles(self):
        command = RegisterRoles()
        command.run()

        roles = RoleModel.query.all()

        for r in roles:
            self.assertEqual(ROLES_MAP[r.id], r.name)

    def test_base_permissions_assignation(self):
        command = RegisterActions()
        command.run()

        command = RegisterViews()
        command.run()

        command = RegisterRoles()
        command.run()

        command = RegisterBasePermissions()
        command.run()

        for base in BASE_PERMISSION_ASSIGNATION:
            for view in self.resources:
                if base[0] in view["resource"].ROLES_WITH_ACCESS:

                    permission = PermissionViewRoleModel.get_permission(
                        base[0],
                        ApiViewModel.query.filter_by(name=view["endpoint"]).first().id,
                        base[1],
                    )

                    self.assertEqual(True, permission)

    def test_argument_parsing_correct(self):
        command = RegisterRoles()
        command.run(verbose="0")

        roles = RoleModel.query.all()

        for r in roles:
            self.assertEqual(ROLES_MAP[r.id], r.name)
