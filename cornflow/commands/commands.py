"""
File with the different defined commands
"""
# Import from libraries
from flask_script import Command, Option
import os

# Import from internal modules
from cornflow.models import UserModel


class CreateSuperAdmin(Command):
    """
    Creates the initial super user that is used by airflow to write the results of the execution back
    This command should only be used on deployment
    """

    # def __init__(self, user, password):
    #
    #     self.user = user
    #     self.password = password

    def get_options(self):
        return (
            Option('-u', '--user',
                   dest='user',
                   help='Superadmin username'),
            Option('-p', '--password',
                   dest='password',
                   help='Superadmin password')
        )

    def run(self, user, password):
        """
        Method to run the command and create the superuser
        It does not return anything
        """
        # SADMIN_USER = os.getenv('SADMIN_USER')
        # SADMIN_PWD = os.getenv('SADMIN_PWD')
        SADMIN_USER = user
        SADMIN_PWD = password
        sadmin_user = UserModel.get_one_user_by_email(SADMIN_USER)
        if sadmin_user is not None:
            if not sadmin_user.super_admin:
                sadmin_user.super_admin = 1
                sadmin_user.save()
            print('Airflow super user already exists')
            return
        user = UserModel(data=dict(name='airflow', email=SADMIN_USER, password=SADMIN_PWD))
        user.super_admin = True
        user.save()
        print('Airflow super user created successfully')
        return


class CleanHistoricData(Command):
    """

    """
    # TODO: implement command to delete data than is older than X years (this time could be read from a settings file)
    def run(self):
        """

        :return:
        :rtype:
        """
        pass
