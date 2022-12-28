"""
This file has several validators used on cornflow core
"""
import re
from typing import Tuple, Union

from jsonschema import Draft7Validator
from marshmallow import ValidationError
from cornflow_core.exceptions import InvalidUsage
from disposable_email_domains import blocklist


def is_special_character(character):
    """
    Method to return if a character is a special character

    :param str character:
    :return: a boolean if the character is a special character or not
    :rtype: bool
    """
    return character in [char for char in "!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\"]


def check_password_pattern(password: str):
    """
    Method to validate the pattern of a password

    :param str password: password to be validated
    :return: a boolean if the password is validated or not
    :rtype: bool
    """
    # TODO: handle better None passwords that can be found when using ldap
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


def check_email_pattern(email: str) -> Tuple[bool, Union[str, None]]:
    """
    Method to check if the provided email is valid. It performs a check against a disposable domains list

    :param str email: the email to validate
    :return: a boolean if the email is valid
    :rtype: bool
    """
    email_pattern = r"\b[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if re.match(email_pattern, email) is None:
        return False, "Invalid email address."
    domain = email.split("@")[1]
    if domain in blocklist:
        return False, "Invalid email address"
    return True, None


def validate_and_continue(obj, data):
    """
    Method to validate data against an object
    """
    try:
        validate = obj.load(data)
    except ValidationError as e:
        raise InvalidUsage(error=f"Bad data format: {e}")
    err = ""
    if validate is None:
        raise InvalidUsage(error=f"Bad data format: {err}")
    return validate


def json_schema_validate(schema: dict, data: dict) -> list:
    """
    Method to validate some data against a json schema

    :param dict schema:the json schema in dict format.
    :param dict data: the data to validate in dict format
    :return: a list with the errors found
    :rtype: list
    """
    validator = Draft7Validator(schema)
    if not validator.is_valid(data):
        return [e for e in validator.iter_errors(data)]
    return []


"""
Aliases
"""
marshmallow_validate_and_continue = validate_and_continue
