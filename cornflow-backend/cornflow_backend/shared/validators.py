"""

"""
import re
from marshmallow import ValidationError
from cornflow_backend.exceptions import InvalidUsage


def is_special_character(character):
    return character in [char for char in "!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\"]


def check_password_pattern(password: str):
    # TODO: handle better None passwords that can be found when using ldap
    # TODO: add maximum password length based on bcrypt specification (72 bytes on UTF8 representation)
    if password is None:
        return True, None
    if len(password) < 5:
        return False, "Password must contain at least 5 characters."
    if password.islower() or password.isupper():
        return False, "Password must contain uppercase and lowercase letters."
    if len(list(filter(str.isdigit, password))) == 0:
        return (
            False,
            "Password must contain at least one number and one special character.",
        )

    if len(list(filter(is_special_character, password))) == 0:
        return (
            False,
            "Password must contain at least one number and one special character.",
        )

    return True, None


def check_email_pattern(email: str):
    email_pattern = r"\b[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if re.match(email_pattern, email) is None:
        return False, "Invalid email address."
    return True, None


def validate_and_continue(obj, data):
    try:
        validate = obj.load(data)
    except ValidationError as e:
        raise InvalidUsage(error=f"Bad data format: {e}")
    err = ""
    if validate is None:
        raise InvalidUsage(error=f"Bad data format: {err}")
    return validate
