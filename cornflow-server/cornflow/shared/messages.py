"""

"""
# Imports from libraries
import smtplib

# Partial imports
from flask import current_app

# Imports from internal modules
from cornflow_backend.exceptions import InvalidData


def get_pwd_email(pwd, email_config):
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    message = MIMEMultipart("alternative")
    message["Subject"] = "Cornflow - Temporary password"
    message["From"] = email_config["email_sender"]
    message["To"] = email_config["email_receiver"]

    html = f"""
    <html>
        <body> 
            <p>
                <p> Hi, </p>
                Here is your temporary password to access cornflow: <big><b>{pwd}</b></big>.<br>
                You can use it to login and then change your password. Please change your password as soon as you can.
                Your older password has been disabled.
            </p>
            <p>Cornflow</p>
        </body>
    </html>
    """

    t = MIMEText(html, "html")

    message.attach(t)

    message.attach(t)

    return message.as_string()


def send_email_to(email_text, email_config):
    port = email_config["port"]
    smtp_server = email_config["server"]
    email_sender = email_config["email_sender"]
    password = email_config["password"]
    email_receiver = email_config["email_receiver"]

    with smtplib.SMTP_SSL(smtp_server, port) as server:
        try:
            server.login(email_sender, password)
        except smtplib.SMTPAuthenticationError:
            raise InvalidData(
                "There is an error with the email provider. Please contact administration."
            )
        try:
            server.sendmail(email_sender, email_receiver, email_text)
        except smtplib.SMTPRecipientsRefused:
            raise InvalidData(
                "There is an error with the email provider. Please contact administration."
            )
