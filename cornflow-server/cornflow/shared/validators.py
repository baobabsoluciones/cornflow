"""
This file has several validators
"""

import re
from difflib import SequenceMatcher
from typing import Tuple, Union

from flask import current_app
from jsonschema import Draft7Validator, validators
from disposable_email_domains import blocklist
from zxcvbn import zxcvbn

from cornflow.shared.const import (
    DEFAULT_PWD_MAX_SIMILARITY,
    DEFAULT_PWD_MIN_LENGTH,
    DEFAULT_PWD_MIN_ZXCVBN_SCORE,
    EMAIL_PATTERN,
    MIN_PERSONAL_TOKEN_LENGTH,
    PASSWORD_SPECIAL_CHARACTERS,
    PWD_FORBIDDEN_DIGIT_SEQUENCE_LENGTH,
)


def _get_config_value(key: str, default):
    """
    Reads a value from the application config, falling back to the given
    default when there is no application context (e.g. some CLI usages).
    """
    try:
        value = current_app.config.get(key, default)
    except RuntimeError:
        return default
    if value is None:
        return default
    try:
        return type(default)(value)
    except (TypeError, ValueError):
        return default


def is_special_character(character):
    """
    Method to return if a character is a special character

    :param str character:
    :return: a boolean if the character is a special character or not
    :rtype: bool
    """
    return character in PASSWORD_SPECIAL_CHARACTERS


def _get_personal_tokens(user_data: dict) -> list:
    """
    Extracts the pieces of personal information (username, names and email
    local part) that must not appear inside a password.

    :param dict user_data: dict with username, first_name, last_name and email
    :return: the list of lowercase personal tokens
    :rtype: list
    """
    if not user_data:
        return []
    tokens = []
    for key in ("username", "first_name", "last_name"):
        value = user_data.get(key)
        if value:
            tokens.append(str(value))
    email = user_data.get("email")
    if email:
        local_part = str(email).split("@")[0]
        tokens.append(local_part)
        tokens.extend(re.split(r"[._-]", local_part))
    return [token.lower() for token in tokens if len(token) >= MIN_PERSONAL_TOKEN_LENGTH]


def check_password_pattern(
    password: str, user_data: dict = None
) -> Tuple[bool, Union[str, None]]:
    """
    Method to validate the pattern of a password following the CCN-STIC-807
    hardening guidelines: minimum length, character variety, no personal
    information, no long digit sequences (dates, phone numbers...) and a
    minimum zxcvbn strength score that rejects common or leaked passwords
    while allowing long passphrases.

    :param str password: password to be validated
    :param dict user_data: optional dict with the user's username, first_name,
      last_name and email, used to reject passwords containing personal data
    :return: a tuple with a boolean (valid or not) and the error message
    :rtype: Tuple[bool, Union[str, None]]
    """
    # TODO: handle better None passwords that can be found when using ldap
    if password is None:
        return True, None
    min_length = _get_config_value("PWD_MIN_LENGTH", DEFAULT_PWD_MIN_LENGTH)
    if len(password) < min_length:
        return False, f"Password must contain at least {min_length} characters."
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number."
    if not any(is_special_character(char) for char in password):
        return False, "Password must contain at least one special character."
    if any(char.isspace() for char in password):
        return False, "Password must not contain whitespace characters."
    if re.search(rf"\d{{{PWD_FORBIDDEN_DIGIT_SEQUENCE_LENGTH},}}", password):
        return (
            False,
            f"Password must not contain sequences of "
            f"{PWD_FORBIDDEN_DIGIT_SEQUENCE_LENGTH} or more digits "
            "(such as dates or phone numbers).",
        )

    personal_tokens = _get_personal_tokens(user_data)
    password_lower = password.lower()
    for token in personal_tokens:
        if token in password_lower:
            return (
                False,
                "Password must not contain your username, name or email address.",
            )

    min_score = _get_config_value(
        "PWD_MIN_ZXCVBN_SCORE", DEFAULT_PWD_MIN_ZXCVBN_SCORE
    )
    result = zxcvbn(password, user_inputs=personal_tokens or None)
    if result["score"] < min_score:
        warning = (result.get("feedback") or {}).get("warning") or (
            "It is too similar to commonly used passwords or patterns."
        )
        return False, f"Password is too easy to guess. {warning}"

    return True, None


def passwords_too_similar(new_password: str, old_password: str) -> bool:
    """
    Checks whether two passwords are too similar to one another (e.g. only a
    number was rotated). Used to prevent trivial variations of the previous
    password when it is changed.

    :param str new_password: the candidate password
    :param str old_password: the password being replaced
    :return: True if the passwords are too similar
    :rtype: bool
    """
    if new_password is None or old_password is None:
        return False
    threshold = _get_config_value("PWD_MAX_SIMILARITY", DEFAULT_PWD_MAX_SIMILARITY)
    ratio = SequenceMatcher(
        None, new_password.lower(), old_password.lower()
    ).ratio()
    return ratio >= threshold


def check_email_pattern(email: str) -> Tuple[bool, Union[str, None]]:
    """
    Method to check if the provided email is valid. It performs a check against a disposable domains list

    :param str email: the email to validate
    :return: a boolean if the email is valid
    :rtype: bool
    """
    if re.match(EMAIL_PATTERN, email) is None:
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
