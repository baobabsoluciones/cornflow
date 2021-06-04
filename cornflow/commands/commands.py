"""
File with the different defined commands
"""
# Import from libraries
from flask_script import Command, Option

# Import from internal modules
from cornflow.models import (
    ActionModel,
    ApiViewModel,
    PermissionViewRoleModel,
    RoleModel,
    UserModel,
    UserRoleModel,
)
from cornflow.shared.const import (
    BASE_ACTIONS,
    BASE_PERMISSION_ASSIGNATION,
    BASE_ROLES,
    SERVICE_ROLE,
)
from cornflow.endpoints import resources
from cornflow.shared.utils import db


class CreateServiceUser(Command):
    """
    Creates the initial super user that is used by airflow to write the results of the execution back
    This command should only be used on deployment
    """

    def get_options(self):
        return (
            Option("-u", "--user", dest="user", help="Service user username"),
            Option("-p", "--password", dest="password", help="Service user password"),
        )

    def run(self, user, password):
        """
        Method to run the command and create the superuser
        It does not return anything
        """
        SERVICE_NAME = user
        SERVICE_PASSWORD = password
        service_user = UserModel.get_one_user_by_email(SERVICE_NAME)
        if service_user is not None:
            if not service_user.super_admin:
                service_user.super_admin = 1
                service_user.save()
            print("Airflow super user already exists")
            return
        user = UserModel(
            data=dict(name="airflow", email=SERVICE_NAME, password=SERVICE_PASSWORD)
        )
        user.super_admin = True
        user.save()
        user_role = UserRoleModel({"user_id": user.id, "role_id": SERVICE_ROLE})
        user_role.save()
        return


class CleanHistoricData(Command):
    """ """

    # TODO: implement command to delete data than is older than X years (this time could be read from a settings file)
    def run(self):
        """

        :return:
        :rtype:
        """
        pass


class RegisterActions(Command):
    def run(self):
        # TODO: empty table beforehand
        actions_list = [
            ActionModel(id=key, name=value) for key, value in BASE_ACTIONS.items()
        ]
        db.session.bulk_save_objects(actions_list)
        db.session.commit()

        return


class RegisterViews(Command):
    def run(self):
        # TODO: empty table beforehand
        views_list = [
            ApiViewModel(
                {
                    "name": view["endpoint"],
                    "url_rule": view["urls"],
                    "description": view["resource"].DESCRIPTION,
                }
            )
            for view in resources
        ]
        db.session.bulk_save_objects(views_list)
        db.session.commit()

        return


class UpdateViews(Command):
    def run(self):
        views_list = [
            ApiViewModel(
                {
                    "name": view["endpoint"],
                    "url_rule": view["urls"],
                    "description": view["resource"].DESCRIPTION,
                }
            )
            for view in resources
            if ApiViewModel.get_one_by_name(view["endpoint"]) is None
        ]
        db.session.bulk_save_objects(views_list)
        db.session.commit()

        return


class RegisterRoles(Command):
    def run(self):
        role_list = [
            RoleModel({"id": key, "name": value}) for key, value in BASE_ROLES.items()
        ]
        db.session.bulk_save_objects(role_list)
        db.session.commit()

        return


class BasePermissionAssignationRegistration(Command):
    def run(self):

        assign_list = [
            PermissionViewRoleModel(
                {
                    "role_id": perm[0],
                    "action_id": perm[1],
                    "api_view_id": ApiViewModel.query.filter_by(name=view["endpoint"])
                    .first()
                    .id,
                }
            )
            for perm in BASE_PERMISSION_ASSIGNATION
            for view in resources
            if perm[0] in view["resource"].ROLES_WITH_ACCESS
        ]

        db.session.bulk_save_objects(assign_list)
        db.session.commit()

        return


class SecurityInitialization(Command):
    def run(self):
        RegisterActions().run()
        RegisterViews().run()
        RegisterRoles().run()
        BasePermissionAssignationRegistration().run()
        return
