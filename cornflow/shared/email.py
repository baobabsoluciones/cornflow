# Imports from libraries
import ssl, smtplib
from flask import current_app

# Imports from internal modules
from ..shared.exceptions import InvalidUsage, InvalidCredentials


def get_pwd_email(pwd, receiver_email):
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    sender_email = current_app.config["CORNFLOW_EMAIL_ADDRESS"]

    message = MIMEMultipart("alternative")
    message["Subject"] = "Cornflow - Temporary password"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"""\
        Hi,
        Here is your temporary password to access cornflow: {pwd}.
        You can use it to login and then change your password. Please change your password as soon as you can. 

        Cornflow
        """

    t = MIMEText(text, "plain")
    message.attach(t)

    return message.as_string()


def send_email_to(email_text, email_receiver):
    port = 465
    smtp_server = "smtp.gmail.com"
    email_sender = current_app.config["CORNFLOW_EMAIL_ADDRESS"]
    password = current_app.config["CORNFLOW_EMAIL_PASSWORD"]
    context = ssl.create_default_context()
    if email_sender is None or password is None:
        raise InvalidUsage(
            "This functionality is not available. "
            + "Check that cornflow's email is correctly configured"
        )
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        try:
            server.login(email_sender, password)
        except smtplib.SMTPAuthenticationError:
            raise InvalidUsage(
                "This functionality is not available. "
                + "Check that cornflow's email is correctly configured"
            )
        try:
            server.sendmail(email_sender, email_receiver, email_text)
        except smtplib.SMTPRecipientsRefused:
            raise InvalidCredentials("The provided email address is invalid")
