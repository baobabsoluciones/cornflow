"""
This file has methods to be able to send emails from an API REST
And some specific methods from some typical emails.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPRecipientsRefused

from cornflow_core.exceptions import InvalidData


def get_email(text: str, subject: str, sender: str, receiver: str):
    """
    This method is used to get the email object needed for the send_email_to method.

    :param str text: The text of the email as a html in plain text
    :param str subject: The subject of the email
    :param str sender: The email address from which the email is going to be sent
    :param str receiver: The email address to receive the email
    :return: The email as a string to be sent
    :rtype: str
    """

    email = MIMEMultipart("alternative")
    email["Subject"] = f"{subject}"
    email["From"] = f"{sender}"
    email["To"] = f"{receiver}"

    body = f"{text}"

    t = MIMEText(body, "html")

    email.attach(t)
    email.attach(t)

    return email.as_string()


def get_password_recover_email(
    temp_password: str, service_name: str, sender: str, receiver: str
):
    """
    This method is used to get the email object needed for the send_email_to method to sent a new password to a user

    :param str temp_password: The temporal password to be sent.
    :param str service_name: The name of the service that is sending the password that is going to appear
    on the subject and on the body
    :param str sender: The email address from which the email is going to be sent.
    :param str receiver: The email address to receive the email.
    :return: The email as a string to be sent
    :rtype: str
    """
    text_template = f"""
    <html>
        <body> 
            <p>
                <p> Hi, </p>
                Here is your temporary password to access {service_name}: <big><b>{temp_password}</b></big>.<br>
                You can use it to login and then change your password. Please change your password as soon as you can.
                Your older password has been disabled.
            </p>
            <p>{service_name}</p>
        </body>
    </html>
    """
    subject = f"{service_name} - Temporary password"
    return get_email(text_template, subject, sender, receiver)


def send_email_to(
    email: str, smtp_server: str, port: int, sender: str, password: str, receiver: str
):
    """
    This method sends an email

    :param str email: The email to be sent
    :param str smtp_server: The SMTP Server that has to send the email.
    :param int port: The port of the SMTP Server.
    :param str sender: The email address from which the email is going to be sent
    :param str password: The password of the sender email address
    :param str receiver: The email address to receive the email
    :return: None
    :rtype: None
    """
    with SMTP_SSL(smtp_server, port) as server:
        try:
            server.login(sender, password)
        except SMTPAuthenticationError:
            raise InvalidData(
                "There is an error with the email provider. Please contact administration"
            )

        try:
            server.sendmail(sender, receiver, email)
        except SMTPRecipientsRefused:
            raise InvalidData(
                "There is an error with the email provider. Please contact administration"
            )
