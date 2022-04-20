"""
This file has methods to be able to send emails from an API REST
And some specific methods from some typical emails.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPAuthenticationError, SMTPRecipientsRefused

from cornflow_core.exceptions import InvalidData


def get_email(text, subject, sender, receiver, **kwargs):
    """

    :param text:
    :type text:
    :param subject:
    :type subject:
    :param sender:
    :type sender:
    :param receiver:
    :type receiver:
    :return:
    :rtype:
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


def get_password_recover_email(temp_password, service_name, sender, receiver, **kwargs):
    """

    :param temp_password:
    :type temp_password:
    :param service_name:
    :type service_name:
    :param sender:
    :type sender:
    :param receiver:
    :type receiver:
    :return:
    :rtype:
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


def send_email_to(email, smtp_server, port, sender, password, receiver, **kwargs):
    """

    :param email:
    :type email:
    :param smtp_server:
    :type smtp_server:
    :param port:
    :type port:
    :param sender:
    :type sender:
    :param password:
    :type password:
    :param receiver:
    :type receiver:
    :return:
    :rtype:
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
