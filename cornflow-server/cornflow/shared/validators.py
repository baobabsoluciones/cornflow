"""
This file has several validators
"""

import re
from typing import Tuple, Union

from jsonschema import Draft7Validator, validators
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


def extend_with_default(validator_class):
    """
    Method to extend a validator, so it extends the data with the default values defined on the jsonschema
    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for prop, sub in properties.items():
            if "default" in sub:
                instance.setdefault(prop, sub["default"])
        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(validator_class, {"properties": set_defaults})


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


def json_schema_extend_and_validate(schema: dict, data: dict) -> Tuple[dict, list]:
    """
    Method to validate som data, extend it with default values and give back the processed errors

    :param dict schema: the json schema in dict format.
    :param dict data: the data to validate in dict format
    :return: a tuple with the data extended and the errors found
    :rtype: tuple
    """
    data_cp = dict(data)
    default_validator = extend_with_default(Draft7Validator)
    validator = default_validator(schema)
    if not validator.is_valid(data_cp):
        return data_cp, [e for e in validator.iter_errors(data_cp)]
    return data_cp, []


def json_schema_validate_as_string(schema: dict, data: dict) -> list:
    """
    Method to validate some data against a json schema

    :param dict schema:the json schema in dict format.
    :param dict data: the data to validate in dict format
    :return: a list with the errors found
    :rtype: list
    """
    return [str(e) for e in json_schema_validate(schema, data)]


def json_schema_extend_and_validate_as_string(
    schema: dict, data: dict
) -> Tuple[dict, list]:
    """
    Method to extend the schema with default values and give back the processed error

    :param dict schema: the json schema in dict format.
    :param dict data: the data to validate in dict format
    :return: a tuple with the data extended and the errors found
    :rtype: tuple
    """
    data_cp, errors = json_schema_extend_and_validate(schema, data)
    return data_cp, [str(e) for e in errors]
