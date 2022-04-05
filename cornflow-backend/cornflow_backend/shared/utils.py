"""

"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from .exceptions import InvalidCredentials
import re

database = SQLAlchemy()
password_crypt = Bcrypt()


def check_password_pattern(password: str):
    if len(password) < 5:
        raise InvalidCredentials("Password must contain at least 5 characters.")
    if password.islower() or password.isupper():
        raise InvalidCredentials(
            "Password must contain uppercase and lowercase letters."
        )
    if len(list(filter(str.isdigit, password))) == 0:
        raise InvalidCredentials(
            "Password must contain at least one number and one special character."
        )

    def is_special_character(character):
        return character in [char for char in "!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\"]

    if len(list(filter(is_special_character, password))) == 0:
        raise InvalidCredentials(
            "Password must contain at least one number and one special character."
        )
    return True


def check_email_pattern(email: str):
    email_pattern = r"\b[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if re.match(email_pattern, email) is None:
        raise InvalidCredentials("Invalid email address.")
    return True
