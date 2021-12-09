"""
File with the different defined commands
"""

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

# username_option = Option(
#     "-u", "--username", dest="username", help="User username", type=str
# )
# email_option = Option("-e", "--email", dest="email", help="User email", type=str)
# password_option = Option(
#     "-p", "--password", dest="password", help="User password", type=str
# )
#
# verbose_option = Option(
#     "-v",
#     "--verbose",
#     dest="verbose",
#     help="Verbose for the command. 0 no verbose, 1 full verbose",
#     type=int,
# )


def create_user_with_role(username, email, password, name, role, verbose=0):
    """
    Method to create a user with a given email, password and name

    :param str username: username for the new user
    :param str email: email for the new user
    :param str password: password for the new user
    :param str name: name for the new user
    :param int role: role for the new user
    :param int verbose: verbose of the function
    :return: a boolean if the execution went well
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
    user_actual_roles = [ur.role for ur in user_role]
    if user_role is not None and RoleModel.get_one_object(role) in user_actual_roles:
        if verbose == 1:
            print("{} exists and already has service role assigned".format(name))
        return True

    user_role = UserRoleModel({"user_id": user.id, "role_id": role})
    user_role.save()
    if verbose == 1:
        print("{} already exists and is assigned a service role".format(name))
    return True


def create_service_user_command(username, email, password, verbose=0):
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


def create_admin_user_command(username, email, password, verbose=0):
    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "admin", ADMIN_ROLE, verbose
    )


def register_actions_command(verbose=0):
    actions_registered = [ac.name for ac in ActionModel.get_all_objects()]

    db.session.commit()

    actions_to_register = [
        ActionModel(id=key, name=value)
        for key, value in ACTIONS_MAP.items()
        if value not in actions_registered
    ]

    if len(actions_to_register) > 0:
        db.session.bulk_save_objects(actions_to_register)

    db.session.commit()
    print(db.session.get_bind())

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('actions', 'id'), MAX(id)) FROM actions;"
        )
        db.session.commit()

    if verbose == 1:
        if len(actions_to_register) > 0:
            print("Actions registered: ", actions_to_register)
        else:
            print("No new actions to be registered")

    return True


def register_views_command(verbose=0):
    views_registered = [view.name for view in ApiViewModel.get_all_objects()]

    db.session.commit()

    views_to_register = [
        ApiViewModel(
            {
                "name": view["endpoint"],
                "url_rule": view["urls"],
                "description": view["resource"].DESCRIPTION,
            }
        )
        for view in resources
        if view["endpoint"] not in views_registered
    ]

    if len(views_to_register) > 0:
        db.session.bulk_save_objects(views_to_register)

    db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('api_view', 'id'), MAX(id)) FROM api_view;"
        )
        db.session.commit()

    if verbose == 1:
        if len(views_to_register) > 0:
            print("Endpoints registered: ", views_to_register)
        else:
            print("No new endpoints to be registered")

    return True


def register_roles_command(verbose=0):
    roles_registered = [role.name for role in RoleModel.get_all_objects()]

    db.session.commit()

    roles_to_register = [
        RoleModel({"id": key, "name": value})
        for key, value in ROLES_MAP.items()
        if value not in roles_registered
    ]

    if len(roles_to_register) > 0:
        db.session.bulk_save_objects(roles_to_register)

    db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
        )
        db.session.commit()

    if verbose == 1:
        if len(roles_to_register) > 0:
            print("Roles registered: ", roles_to_register)
        else:
            print("No new roles to be registered")

    return True


def register_base_permissions_command(verbose=0):
    permissions_registered = [
        (perm.action_id, perm.api_view_id, perm.role_id)
        for perm in PermissionViewRoleModel.get_all_objects()
    ]

    db.session.commit()
    views = {view.name: view.id for view in ApiViewModel.get_all_objects()}

    # Create base permissions
    permissions_to_register = [
        PermissionViewRoleModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views[view["endpoint"]],
            }
        )
        for role, action in BASE_PERMISSION_ASSIGNATION
        for view in resources
        if role in view["resource"].ROLES_WITH_ACCESS
        and (
            action,
            views[view["endpoint"]],
            role,
        )
        not in permissions_registered
    ] + [
        PermissionViewRoleModel(
            {
                "role_id": role,
                "action_id": action,
                "api_view_id": views[endpoint],
            }
        )
        for role, action, endpoint in EXTRA_PERMISSION_ASSIGNATION
        if (
            action,
            views[endpoint],
            role,
        )
        not in permissions_registered
    ]

    if len(permissions_to_register) > 0:
        db.session.bulk_save_objects(permissions_to_register)

    db.session.commit()

    if "postgres" in str(db.session.get_bind()):
        db.engine.execute(
            "SELECT setval(pg_get_serial_sequence('permission_view', 'id'), MAX(id)) FROM permission_view;"
        )
        db.session.commit()

    if verbose == 1:
        if len(permissions_to_register) > 0:
            print("Permissions registered: ", permissions_to_register)
        else:
            print("No new permissions to register")

    return True


def access_initialization_command(verbose=0):
    register_actions_command(verbose)
    register_views_command(verbose)
    register_roles_command(verbose)
    register_base_permissions_command(verbose)
    if verbose == 1:
        print("Access initialization ran successfully")
    return True


# class CleanHistoricData(Command):
#     """ """
#
#     # TODO: implement command to delete data than is older than X years (this time could be read from a settings file)
#     def run(self):
#         """
#
#         :return:
#         :rtype:
#         """
#         pass
#
#
