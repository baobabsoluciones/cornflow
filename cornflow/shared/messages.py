"""

"""
# Imports from libraries
import smtplib
import ssl

# Partial imports
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


def send_email_to(email_text, email_receiver):
    port = current_app.config["CORNFLOW_EMAIL_PORT"]
    smtp_server = current_app.config["CORNFLOW_EMAIL_SERVER"]
    email_sender = current_app.config["CORNFLOW_EMAIL_ADDRESS"]
    password = current_app.config["CORNFLOW_EMAIL_PASSWORD"]
    context = ssl.create_default_context()
    if email_sender is None or password is None or port is None or smtp_server is None:
        raise InvalidUsage(
            "This functionality is not available. Check that cornflow's email is correctly configured"
        )
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        try:
            server.login(email_sender, password)
        except smtplib.SMTPAuthenticationError:
            raise InvalidUsage(
                "This functionality is not available. Check that cornflow's email is correctly configured"
            )
        try:
            server.sendmail(email_sender, email_receiver, email_text)
        except smtplib.SMTPRecipientsRefused:
            raise InvalidCredentials("The provided email address is invalid")
