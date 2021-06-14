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
    ADMIN_ROLE,
    ACTIONS_MAP,
    BASE_PERMISSION_ASSIGNATION,
    EXTRA_PERMISSION_ASSIGNATION,
    ROLES_MAP,
    SERVICE_ROLE,
)
from cornflow.endpoints import resources
from cornflow.shared.utils import db

username_option = Option(
    "-u", "--username", dest="username", help="User username", type=str
)
email_option = Option("-e", "--email", dest="email", help="User email", type=str)
password_option = Option(
    "-p", "--password", dest="password", help="User password", type=str
)

verbose_option = Option(
    "-v",
    "--verbose",
    dest="verbose",
    help="Verbose for the command. 0 no verbose, 1 full verbose",
    type=int,
)


def create_user_with_role(username, email, password, name, role, verbose=0):
    """
    Method to create a user with a given email, password and name

    :param str username: username for the new user
    :param str email: email for the new user
    :param str password: password for the new user
    :param str name: name for the new user
    :param int role: role for the new user
    :param int verbose: verbose of the function
    :return: a boolean if the execution went right
    :rtype: bool
    """
    user = UserModel.get_one_user_by_username(username)

    if user is None:
        data = dict(username=username, email=email, password=password)
        user = UserModel(data=data)
        user.save()
        user_role = UserRoleModel({"user_id": user.id, "role_id": role})
        user_role.save()
        if verbose == 1:
            print("{} is created and assigned service role".format(name))
        return True

    user_role = UserRoleModel.get_one_user(user.id)
    if user_role is not None and RoleModel.get_one_object(role) in user_role:
        if verbose == 1:
            print("{} exists and already has service role assigned".format(name))
        return True

    user_role = UserRoleModel({"user_id": user.id, "role_id": role})
    user_role.save()
    if verbose == 1:
        print("{} already exists and is assigned a service role".format(name))
    return True


class CreateServiceUser(Command):
    """
    Creates the initial super user that is used by airflow to write the results of the execution back
    This command should only be used on deployment
    """

    def get_options(self):
        return (
            username_option,
            email_option,
            password_option,
            verbose_option,
        )

    def run(self, username, email, password, verbose=0):
        """
        Method to run the command and create the service user

        :param str username: the username for the service user
        :param str email: the email for the service user
        :param str password: the password for the service user
        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
        if username is None or email is None or password is None:
            print("Missing required arguments")
            return False
        return create_user_with_role(
            username, email, password, "serviceuser", SERVICE_ROLE, verbose
        )


class CreateAdminUser(Command):
    def get_options(self):
        return (
            username_option,
            email_option,
            password_option,
            verbose_option,
        )

    def run(self, username, email, password, verbose=0):
        """
        Method to run and create the admin user

        :param str username: the username for the service user
        :param str email: the email for the admin user
        :param str password: the password for the admin user
        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
        if username is None or email is None or password is None:
            print("Missing required arguments")
            return False
        return create_user_with_role(
            username, email, password, "admin", ADMIN_ROLE, verbose
        )


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
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to register the actions on the database

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
        ActionModel.query.delete()
        db.session.commit()

        actions_list = [
            ActionModel(id=key, name=value) for key, value in ACTIONS_MAP.items()
        ]
        db.session.bulk_save_objects(actions_list)
        db.session.commit()

        if verbose == 1:
            print("Actions successfully registered")

        return True


class RegisterViews(Command):
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to register the endpoints in cornflow

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
        ApiViewModel.query.delete()
        db.session.commit()

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

        if verbose == 1:
            print("Endpoints successfully registered")

        return True


class UpdateViews(Command):
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to update the views that are registered on the database

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
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

        if verbose == 1:
            print("Views successfully updated")

        return


class RegisterRoles(Command):
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to register the roles in cornflow

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """

        RoleModel.query.delete()
        db.session.commit()

        role_list = [
            RoleModel({"id": key, "name": value}) for key, value in ROLES_MAP.items()
        ]
        db.session.bulk_save_objects(role_list)
        db.session.commit()

        if verbose == 1:
            print("Roles successfully registered")

        return


class RegisterBasePermissions(Command):
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to register the base permissions

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """

        PermissionViewRoleModel.query.delete()
        db.session.commit()

        # Create base permissions
        assign_list = [
            PermissionViewRoleModel(
                {
                    "role_id": role,
                    "action_id": action,
                    "api_view_id": ApiViewModel.query.filter_by(name=view["endpoint"])
                    .first()
                    .id,
                }
            )
            for role, action in BASE_PERMISSION_ASSIGNATION
            for view in resources
            if role in view["resource"].ROLES_WITH_ACCESS
        ]

        db.session.bulk_save_objects(assign_list)
        db.session.commit()

        # Create extra permissions
        assign_list = [
            PermissionViewRoleModel(
                {
                    "role_id": role,
                    "action_id": action,
                    "api_view_id": ApiViewModel.query.filter_by(name=endpoint)
                    .first()
                    .id,
                }
            )
            for role, action, endpoint in EXTRA_PERMISSION_ASSIGNATION
        ]

        db.session.bulk_save_objects(assign_list)
        db.session.commit()

        if verbose == 1:
            print("Base permissions successfully registered")

        return True


class AccessInitialization(Command):
    def get_options(self):
        return (verbose_option,)

    def run(self, verbose=0):
        """
        Method to run all access commands together

        :param int verbose: verbose of the command
        :return: a boolean if the execution went right
        :rtype: bool
        """
        RegisterActions().run(verbose)
        RegisterViews().run(verbose)
        RegisterRoles().run(verbose)
        RegisterBasePermissions().run(verbose)
        if verbose == 1:
            print("Access initialization ran successfully")
        return True
