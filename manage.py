import click
from cornflow.commands import *
from flask.cli import FlaskGroup

from cornflow.app import create_app, db

env_name = "development"
app = create_app(env_name)

cli = FlaskGroup(app)

# manager = Manager(app=app)

# User commands
# manager.add_command("create_admin_user", CreateAdminUser)
@cli.command("create_admin_user")
@click.argument("username", "email", "password", "verbose")
def create_admin_user(username, email, password, verbose=0):
    create_admin_user_command(username, email, password, verbose)


# manager.add_command("create_service_user", CreateServiceUser)
@cli.command("create_service_user")
@click.argument("username", "email", "password", "verbose")
def create_service_user(username, email, password, verbose=0):
    create_service_user_command(username, email, password, verbose)


# Access control commands
# manager.add_command("access_init", AccessInitialization)
@cli.command("access_init")
@click.argument("verbose")
def access_init(verbose=0):
    access_initialization_command(verbose)


# manager.add_command("register_base_assignations", RegisterBasePermissions)
@cli.command("register_base_assignations")
@click.argument("verbose")
def register_base_assignations(verbose=0):
    register_base_permissions_command(verbose)


# manager.add_command("register_actions", RegisterActions)
@cli.command("register_actions")
@click.argument("verbose")
def create_actions(verbose=0):
    create_service_user_command(verbose)


# manager.add_command("register_views", RegisterViews)
@cli.command("register_views")
@click.argument("verbose")
def register_views(verbose=0):
    register_views_command(verbose)


# manager.add_command("register_roles", RegisterRoles)
@cli.command("register_roles")
@click.argument("verbose")
def register_roles(verbose=0):
    register_roles_command(verbose)


# # Other commands
# manager.add_command("clean_historic_data", CleanHistoricData)


# if __name__ == "__main__":
#     manager.run()
