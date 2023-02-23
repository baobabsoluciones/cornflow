import os

from .actions import register_actions_command
from .permissions import register_base_permissions_command
from .roles import register_roles_command
from .views import register_views_command


def access_init_command(verbose: bool = False):
    external = int(os.getenv("EXTERNAL_APP", 0))
    external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")

    register_actions_command(verbose)
    register_roles_command(verbose)

    register_views_command(verbose=verbose)
    if external != 0:
        register_views_command(external_app=external_app, verbose=verbose)

    register_base_permissions_command(verbose=verbose)
    if external != 0:
        register_base_permissions_command(external_app=external_app, verbose=verbose)
