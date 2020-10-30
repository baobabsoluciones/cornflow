"""
File with the different defined commands
"""

from flask_script import Command
from flaskr.models.user import UserModel


class CreateSuperAdmin(Command):
    """
    Creates the initial super user that is used by airflow to write the results of the execution back
    This command should only be used on deployment
    """

    # TODO: read email and password from environment variables
    def run(self):
        """
        Method to run the command and create the superuser
        It does not return anything
        """
        data = {'name': 'airflow', 'email': 'airflow@baobabsoluciones.es', 'password': 'THISNEEDSTOBECHANGED'}
        user = UserModel(data=data)
        user.super_admin = True
        user.save()
        print('Airflow super user created successfully')


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
