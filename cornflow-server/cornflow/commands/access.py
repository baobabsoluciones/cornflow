def access_init_command(verbose: bool = False):
    from .actions import register_actions_command
    from .permissions import register_base_permissions_command
    from .roles import register_roles_command
    from .views import register_views_command

    register_actions_command(verbose)
    register_roles_command(verbose)
    register_views_command(verbose)
    register_base_permissions_command(verbose)
