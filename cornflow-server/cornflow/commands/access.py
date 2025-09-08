import logging
import os

from .actions import register_actions_command
from .permissions import register_base_permissions_command
from .roles import register_roles_command
from .views import register_views_command

# Configure logger for access
logger = logging.getLogger("cornflow.access")


def access_init_command(verbose: bool = False):
    """
    Initialize the access to the system.
    """

    external = int(os.getenv("EXTERNAL_APP", 0))
    external_app = os.getenv("EXTERNAL_APP_MODULE", "external_app")

    register_actions_command(verbose)

    if external != 0:
        register_roles_command(external_app=external_app, verbose=verbose)
        register_views_command(external_app=external_app, verbose=verbose)
    else:
        register_roles_command(verbose=verbose)
        register_views_command(verbose=verbose)

    if external != 0:
        register_base_permissions_command(external_app=external_app, verbose=verbose)
    else:
        register_base_permissions_command(verbose=verbose)
