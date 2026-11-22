"""
Helpers to encrypt secrets at rest (such as the TOTP secrets used for
two-factor authentication) using a Fernet key derived from the application
secret key.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from cornflow.shared.exceptions import ConfigurationError, InvalidUsage


def _get_fernet() -> Fernet:
    """
    Builds a Fernet instance with a key derived from SECRET_TOKEN_KEY, the
    effective secret key (FERNET_KEY, else SECRET_KEY).

    :return: the Fernet instance
    :rtype: Fernet
    """
    secret = current_app.config.get("SECRET_TOKEN_KEY")
    if not secret:
        raise ConfigurationError(
            "No secret key is configured (set FERNET_KEY, or SECRET_KEY): "
            "secrets can not be encrypted at rest"
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf8")).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """
    Encrypts a string value so it can be stored at rest.

    :param str value: the plain value
    :return: the encrypted value, base64 encoded
    :rtype: str
    """
    if value is None:
        return None
    return _get_fernet().encrypt(value.encode("utf8")).decode("utf8")


def decrypt_value(value: str) -> str:
    """
    Decrypts a value encrypted with :func:`encrypt_value`.

    :param str value: the encrypted value
    :return: the plain value
    :rtype: str
    """
    if value is None:
        return None
    try:
        return _get_fernet().decrypt(value.encode("utf8")).decode("utf8")
    except InvalidToken:
        raise InvalidUsage(
            "An internal error occurred. Please contact an administrator.",
            status_code=500,
            log_txt="A stored secret could not be decrypted: the secret key "
            "(FERNET_KEY, or SECRET_KEY when FERNET_KEY is not set) is not the "
            "one it was encrypted with. If it is the MFA secret of a user, an "
            "administrator can reset it with DELETE /user/<id>/mfa/.",
        )
