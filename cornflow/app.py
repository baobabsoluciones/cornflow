import click
import os

from flask import Flask
from flask.cli import with_appcontext
from flask_apispec.extension import FlaskApiSpec
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api

from .config import app_config
from .endpoints import resources
from .shared.compress import init_compress
from .shared.exceptions import _initialize_errorhandlers
from .shared.utils import db, bcrypt


def create_app(env_name="development", dataconn=None):
    """

    :param str env_name: 'testing' or 'development' or 'production'
    :return: the application that is going to be running :class:`Flask`
    :rtype: :class:`Flask`
    """
    app = Flask(__name__)
    app.config.from_object(app_config[env_name])
    # initialization for init_cornflow_service.py
    if dataconn is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = dataconn
    CORS(app)
    bcrypt.init_app(app)
    db.init_app(app)
    migrate = Migrate(app=app, db=db)

    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute("pragma foreign_keys=ON")

        with app.app_context():
            from sqlalchemy import event

            event.listen(db.engine, "connect", _fk_pragma_on_connect)

    api = Api(app)
    for res in resources:
        api.add_resource(res["resource"], res["urls"], endpoint=res["endpoint"])

    docs = FlaskApiSpec(app)
    for res in resources:
        docs.register(target=res["resource"], endpoint=res["endpoint"])

    _initialize_errorhandlers(app)
    init_compress(app)

    app.cli.add_command(create_service_user)
    app.cli.add_command(create_admin_user)
    app.cli.add_command(register_roles)
    app.cli.add_command(register_actions)
    app.cli.add_command(register_views)
    app.cli.add_command(register_base_assignations)
    # app.cli.add_command(access_init)

    return app


def create_user_with_role(username, email, password, name, role, verbose=0):
    from .models import RoleModel, UserModel, UserRoleModel

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


@click.command("create_service_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", default=0)
@with_appcontext
def create_service_user(username, email, password, verbose):
    from .shared.const import SERVICE_ROLE

    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "serviceuser", SERVICE_ROLE, verbose
    )


@click.command("create_admin_user")
@click.option("-u", "--username", required=True, type=str)
@click.option("-e", "--email", required=True, type=str)
@click.option("-p", "--password", required=True, type=str)
@click.option("-v", "--verbose", default=0)
@with_appcontext
def create_admin_user(username, email, password, verbose=0):
    from .shared.const import ADMIN_ROLE

    if username is None or email is None or password is None:
        print("Missing required arguments")
        return False
    return create_user_with_role(
        username, email, password, "admin", ADMIN_ROLE, verbose
    )


@click.command("register_roles")
@click.option("-v", "--verbose", default=0)
@with_appcontext
def register_roles(verbose):
    from .models import RoleModel
    from .shared.const import ROLES_MAP

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

    # if "postgres" in str(db.session.get_bind()):
    #     db.engine.execute(
    #         "SELECT setval(pg_get_serial_sequence('roles', 'id'), MAX(id)) FROM roles;"
    #     )
    #     db.session.commit()

    if verbose == 1:
        if len(roles_to_register) > 0:
            print("Roles registered: ", roles_to_register)
        else:
            print("No new roles to be registered")

    return True


@click.command("register_actions")
@click.option("-v", "--verbose", default=0)
@with_appcontext
def register_actions(verbose):
    from .models import ActionModel
    from .shared.const import ACTIONS_MAP

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

    # if "postgres" in str(db.session.get_bind()):
    #     db.engine.execute(
    #         "SELECT setval(pg_get_serial_sequence('actions', 'id'), MAX(id)) FROM actions;"
    #     )
    #     db.session.commit()

    if verbose == 1:
        if len(actions_to_register) > 0:
            print("Actions registered: ", actions_to_register)
        else:
            print("No new actions to be registered")

    return True


@click.command("register_views")
@click.option("-v", "--verbose", default=0)
@with_appcontext
def register_views(verbose):
    from .models import ApiViewModel

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

    # if "postgres" in str(db.session.get_bind()):
    #     db.engine.execute(
    #         "SELECT setval(pg_get_serial_sequence('api_view', 'id'), MAX(id)) FROM api_view;"
    #     )
    #     db.session.commit()

    if verbose == 1:
        if len(views_to_register) > 0:
            print("Endpoints registered: ", views_to_register)
        else:
            print("No new endpoints to be registered")

    return True


@click.command("register_base_assignations")
@click.option("-v", "--verbose", default=0)
@with_appcontext
def register_base_assignations(verbose):
    from .models import ApiViewModel, PermissionViewRoleModel
    from .shared.const import BASE_PERMISSION_ASSIGNATION, EXTRA_PERMISSION_ASSIGNATION

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

    # if "postgres" in str(db.session.get_bind()):
    #     db.engine.execute(
    #         "SELECT setval(pg_get_serial_sequence('permission_view', 'id'), MAX(id)) FROM permission_view;"
    #     )
    #     db.session.commit()

    if verbose == 1:
        if len(permissions_to_register) > 0:
            print("Permissions registered: ", permissions_to_register)
        else:
            print("No new permissions to register")

    return True


# @click.command("access_init")
# @click.option("-v", "--verbose", default=0)
# @with_appcontext
# def access_init(verbose):
#     register_actions(verbose)
#     register_views(verbose)
#     register_roles(verbose)
#     register_base_assignations(verbose)
#     if verbose == 1:
#         print("Access initialization ran successfully")
#     return True


if __name__ == "__main__":
    environment_name = os.getenv("FLASK_ENV", "development")
    # env_name = 'development'
    app = create_app(environment_name)
    app.run()
