from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from cornflow.commands import *

from cornflow.app import create_app, db

env_name = "development"
app = create_app(env_name)

migrate = Migrate(app=app, db=db)
manager = Manager(app=app)

# Database commands
manager.add_command("db", MigrateCommand)

# User commands
manager.add_command("create_admin_user", CreateAdminUser)
manager.add_command("create_service_user", CreateServiceUser)

# Access control commands
manager.add_command("access_init", AccessInitialization)
manager.add_command("register_base_assignations", RegisterBasePermissions)
manager.add_command("register_actions", RegisterActions)
manager.add_command("register_views", RegisterViews)
manager.add_command("register_roles", RegisterRoles)

# Other commands
manager.add_command("clean_historic_data", CleanHistoricData)


if __name__ == "__main__":
    manager.run()
