def create_user_with_role(username, email, password, role_name, role, verbose=0):
    from ..models import RoleModel, UserModel, UserRoleModel

    user = UserModel.get_one_user_by_username(username)

    if user is None:
        data = dict(username=username, email=email, password=password)
        user = UserModel(data=data)
        user.save()
        user_role = UserRoleModel({"user_id": user.id, "role_id": role})
        user_role.save()
        if verbose == 1:
            print(f"User {username} is created and assigned {role_name} role")
        return True

    user_roles = UserRoleModel.get_all_objects(user_id=user.id)
    user_actual_roles = [ur.role for ur in user_roles]
    if user_roles is not None and RoleModel.get_one_object(role) in user_actual_roles:
        if verbose == 1:
            print(f"User {username} exists and already has {role_name} role assigned")
        return True

    user_role = UserRoleModel({"user_id": user.id, "role_id": role})
    user_role.save()
    if verbose == 1:
        print(f"User {username} already exists and is assigned a {role_name} role")
    return True


def create_service_user_command(username, email, password, verbose):
    from ..shared.const import SERVICE_ROLE

    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "serviceuser", SERVICE_ROLE, verbose
    )


def create_admin_user_command(username, email, password, verbose):
    from ..shared.const import ADMIN_ROLE

    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "admin", ADMIN_ROLE, verbose
    )


def create_planner_user_command(username, email, password, verbose):
    from ..shared.const import PLANNER_ROLE

    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "planner", PLANNER_ROLE, verbose
    )
