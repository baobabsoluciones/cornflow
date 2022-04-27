"""
This file contains the base resource to recover a password
"""

from flask import current_app

from cornflow_core.exceptions import ConfigurationError
from cornflow_core.messages import get_password_recover_email, send_email_to
from cornflow_core.models import UserBaseModel
from .meta_resource import BaseMetaResource


class RecoverPasswordBaseEndpoint(BaseMetaResource):
    """
    Endpoint to recover the password
    """

    def __init__(self):
        super().__init__()
        self.data_model = UserBaseModel

    def recover_password(self, email):
        """

        :param str email: The email where the password needs to be sent to
        :return:
        :rtype:
        """
        sender = current_app.config["SERVICE_EMAIL_ADDRESS"]
        password = current_app.config["SERVICE_EMAIL_PASSWORD"]
        smtp_server = current_app.config["SERVICE_EMAIL_SERVER"]
        port = current_app.config["SERVICE_EMAIL_PORT"]
        service_name = current_app.config["SERVICE_NAME"]
        receiver = email

        if sender is None or password is None or smtp_server is None or port is None:
            raise ConfigurationError(
                "This functionality is not available. Check that cornflow's email is correctly configured"
            )

        message = "The password recovery process has started. Check the email inbox."

        user_obj = self.data_model({"email": receiver})
        if not user_obj.check_email_in_use():
            return {"message": message}, 200

        new_password = self.data_model.generate_random_password()

        text_email = get_password_recover_email(
            temp_password=new_password,
            service_name=service_name,
            sender=sender,
            receiver=receiver,
        )

        send_email_to(
            email=text_email,
            smtp_server=smtp_server,
            port=port,
            sender=sender,
            password=password,
            receiver=receiver,
        )

        data = {"password": new_password}
        user_obj = self.data_model.get_one_user_by_email(receiver)
        user_obj.update(data)

        return {"message": message}, 200
