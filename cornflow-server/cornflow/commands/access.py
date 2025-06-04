import os
from flask import current_app
from .actions import register_actions_command
from .permissions import register_base_permissions_command
from .roles import register_roles_command
from .views import register_views_command


def access_init_command(verbose: bool = False):
    current_app.logger.info(
        "------------------------Access init command----------------"
    )
    external = int(os.getenv("EXTERNAL_APP", 0))
    external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")
    current_app.logger.info(f"external: {external}")
    current_app.logger.info(f"external_app: {external_app}")
    current_app.logger.info("registering actions")
    register_actions_command(verbose)
    current_app.logger.info("registering roles")
    register_roles_command(verbose=verbose)
    if external != 0:
        current_app.logger.info(f"registering roles for external_app: {external_app}")
        register_roles_command(external_app=external_app, verbose=verbose)
    current_app.logger.info("registering views")
    register_views_command(verbose=verbose)
    if external != 0:
        current_app.logger.info(f"registering views for external_app: {external_app}")
        register_views_command(external_app=external_app, verbose=verbose)

    current_app.logger.info("registering base permissions")
    register_base_permissions_command(verbose=verbose)
    if external != 0:
        current_app.logger.info(
            f"registering base permissions for external_app: {external_app}"
        )
        register_base_permissions_command(external_app=external_app, verbose=verbose)
    current_app.logger.info("access init command finished")
