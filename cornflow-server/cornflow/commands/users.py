def create_user_with_role(
    username, email, password, role_name, role, verbose: bool = False
):
    from cornflow.models import UserModel, UserRoleModel, RoleModel
    from flask import current_app

    user = UserModel.get_one_user_by_username(username)

    if user is None:
        data = dict(username=username, email=email, password=password)
        user = UserModel(data=data)
        user.save()
        user_role = UserRoleModel({"user_id": user.id, "role_id": role})
        user_role.save()
        if verbose:
            current_app.logger.info(
                f"User {username} is created and assigned {role_name} role"
            )
        return

    user_roles = UserRoleModel.get_all_objects(user_id=user.id)
    user_actual_roles = [ur.role for ur in user_roles]
    if user_roles is not None and RoleModel.get_one_object(role) in user_actual_roles:
        if verbose:
            current_app.logger.info(
                f"User {username} exists and already has {role_name} role assigned"
            )
        return

    user_role = UserRoleModel({"user_id": user.id, "role_id": role})
    user_role.save()
    if verbose:
        current_app.logger.info(
            f"User {username} already exists and is assigned a {role_name} role"
        )


def create_service_user_command(username, email, password, verbose: bool = True):
    from cornflow.shared.const import SERVICE_ROLE
    from flask import current_app

    if username is None or email is None or password is None:
        current_app.logger.info("Missing required arguments")
        return

    create_user_with_role(
        username, email, password, "serviceuser", SERVICE_ROLE, verbose
    )


def create_admin_user_command(username, email, password, verbose: bool = True):
    from cornflow.shared.const import ADMIN_ROLE
    from flask import current_app

    if username is None or email is None or password is None:
        current_app.logger.info("Missing required arguments")
        return

    create_user_with_role(username, email, password, "admin", ADMIN_ROLE, verbose)


def create_planner_user_command(username, email, password, verbose: bool = True):
    from cornflow.shared.const import PLANNER_ROLE
    from flask import current_app

    if username is None or email is None or password is None:
        current_app.logger.info("Missing required arguments")
        return

    create_user_with_role(username, email, password, "planner", PLANNER_ROLE, verbose)
