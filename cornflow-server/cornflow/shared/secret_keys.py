"""
Secret keys: resolution (FERNET_KEY, else SECRET_KEY, else random at level 1)
and per-level checks.

This module never reads os.environ nor the Flask application context, and it
never modifies the mapping it receives. Messages never contain a key value.
"""

import secrets
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Tuple

FERNET_KEY_ENV_VAR = "FERNET_KEY"
SECRET_KEY_ENV_VAR = "SECRET_KEY"
SECRET_BI_KEY_ENV_VAR = "SECRET_BI_KEY"
# Internal: random key of this startup, passed by `cornflow service init` to the
# gunicorn workers (security level 1 without FERNET_KEY / SECRET_KEY). Not for operators.
EPHEMERAL_SECRET_KEY_ENV_VAR = "CORNFLOW_EPHEMERAL_SECRET_KEY"

# Minimum length in bytes of the JWT signing keys. HMAC-SHA256 requires keys
# of at least 256 bits (RFC 7518, section 3.2) and CCN-STIC-807 requires
# equivalent strength for the employed cryptography.
MINIMUM_SECRET_KEY_LENGTH = 32  # bytes

KEY_SOURCE_FERNET_KEY = "FERNET_KEY"
KEY_SOURCE_SECRET_KEY = "SECRET_KEY"
KEY_SOURCE_RANDOM = "random"  # generated at startup (level 1 only)
KEY_SOURCE_MISSING = "missing"  # no key (levels 2 and 3): create_app refuses to start
KEY_SOURCE_CONFIG = "config"  # set by a configuration class (Testing, external apps)

CONFIG_KEY_SECRET_KEY_SOURCE = "SECRET_KEY_SOURCE"
CONFIG_KEY_SECRET_KEYS_DIFFER = "SECRET_KEYS_DIFFER"

GENERATE_KEY_HINT = 'python -c "import secrets; print(secrets.token_hex(32))"'

_MIN_BYTES = MINIMUM_SECRET_KEY_LENGTH
_MIN_BITS = MINIMUM_SECRET_KEY_LENGTH * 8


def generate_secret_key() -> str:
    """Random key of 64 hex characters (32 random bytes)."""
    return secrets.token_hex(32)


def _defined(environ: Mapping[str, str], name: str) -> Optional[str]:
    """The value, or None if unset, empty or only whitespace. Never stripped otherwise."""
    value = environ.get(name)
    if value is None or not str(value).strip():
        return None
    return value


@dataclass(frozen=True)
class ResolvedSecretKeys:
    token_key: Optional[str]  # SECRET_TOKEN_KEY; None only with KEY_SOURCE_MISSING
    source: str  # KEY_SOURCE_*
    keys_differ: bool  # FERNET_KEY and SECRET_KEY both defined and different
    bi_key: Optional[str]  # SECRET_BI_KEY; None if unset or empty

    def __repr__(self):
        return (
            f"ResolvedSecretKeys(source={self.source!r}, "
            f"keys_differ={self.keys_differ}, "
            f"bi_key={'set' if self.bi_key else 'not set'})"
        )


def resolve_secret_keys(
    environ: Mapping[str, str],
    level: int,
    generate: Optional[Callable[[], str]] = None,
) -> ResolvedSecretKeys:
    """
    FERNET_KEY > SECRET_KEY > random (level 1 only). The generator is looked up
    when called, so it can be replaced.
    """
    fernet = _defined(environ, FERNET_KEY_ENV_VAR)
    secret = _defined(environ, SECRET_KEY_ENV_VAR)
    keys_differ = fernet is not None and secret is not None and fernet != secret

    if fernet is not None:
        token_key, source = fernet, KEY_SOURCE_FERNET_KEY
    elif secret is not None:
        token_key, source = secret, KEY_SOURCE_SECRET_KEY
    elif level == 1:
        token_key = _defined(environ, EPHEMERAL_SECRET_KEY_ENV_VAR)
        if token_key is None:
            token_key = (generate or generate_secret_key)()
        source = KEY_SOURCE_RANDOM
    else:
        token_key, source = None, KEY_SOURCE_MISSING

    return ResolvedSecretKeys(
        token_key=token_key,
        source=source,
        keys_differ=keys_differ,
        bi_key=_defined(environ, SECRET_BI_KEY_ENV_VAR),
    )


def apply_secret_keys(config_class: type, resolved: ResolvedSecretKeys) -> type:
    """
    Sets SECRET_TOKEN_KEY, SECRET_BI_KEY, SECRET_KEY_SOURCE and SECRET_KEYS_DIFFER
    on config_class, except the ones declared in config_class.__dict__ (the class
    body wins). Returns the same class.
    """
    values = {
        "SECRET_TOKEN_KEY": resolved.token_key,
        "SECRET_BI_KEY": resolved.bi_key,
        CONFIG_KEY_SECRET_KEY_SOURCE: resolved.source,
        CONFIG_KEY_SECRET_KEYS_DIFFER: resolved.keys_differ,
    }
    for key, value in values.items():
        if key not in config_class.__dict__:
            setattr(config_class, key, value)
    return config_class


def uses_random_secret_key(config: Mapping) -> bool:
    return config.get(CONFIG_KEY_SECRET_KEY_SOURCE) == KEY_SOURCE_RANDOM


def key_length(value: str) -> int:
    return len(str(value).encode("utf8"))


# Messages


def random_key_warning(mfa_enabled: bool) -> str:
    message = (
        "Neither FERNET_KEY nor SECRET_KEY is set: cornflow signs sessions and "
        "API keys with a random secret key generated at startup. Every restart "
        "invalidates all sessions and API keys."
    )
    if mfa_enabled:
        message += (
            " MFA_ENABLED=1: users who set up two-factor authentication will "
            "not be able to log in after a restart until an administrator "
            "resets their MFA with DELETE /user/<id>/mfa/, which also revokes "
            "their sessions and API keys."
        )
    message += (
        f" Set FERNET_KEY to a fixed value of at least {_MIN_BYTES} bytes. "
        f"Generate one with: {GENERATE_KEY_HINT}"
    )
    return message


TOKEN_KEY_MISSING_WARNING = (
    "SECRET_TOKEN_KEY is not set: authentication tokens can not be issued "
    "until FERNET_KEY (or SECRET_KEY) is set"
)


def short_key_warning(label) -> str:
    return (
        f"{label} is shorter than {_MIN_BYTES} bytes ({_MIN_BITS} bits): "
        f"security levels 2 and 3 do not start with it. Set FERNET_KEY to a "
        f"value of at least {_MIN_BYTES} bytes. Generate one with: "
        f"{GENERATE_KEY_HINT}"
    )


def missing_key_error(level) -> str:
    return (
        f"Security level {level} requires a secret key: set FERNET_KEY (or "
        f"SECRET_KEY) to a value of at least {_MIN_BYTES} bytes "
        f"({_MIN_BITS} bits). Generate one with: {GENERATE_KEY_HINT}"
    )


def short_key_error(level, label) -> str:
    return (
        f"Security level {level} requires a secret key of at least "
        f"{_MIN_BYTES} bytes ({_MIN_BITS} bits), but {label} is shorter: set "
        f"FERNET_KEY (or SECRET_KEY) to a value of at least {_MIN_BYTES} "
        f"bytes. Generate one with: {GENERATE_KEY_HINT}"
    )


KEYS_DIFFER_WARNING = (
    "FERNET_KEY and SECRET_KEY are both set and differ: FERNET_KEY is used and "
    "SECRET_KEY is ignored. Remove SECRET_KEY, or give it the same value as "
    "FERNET_KEY."
)

BI_KEY_MISSING_WARNING = (
    "SECRET_BI_KEY is not set: BI tokens can not be issued until it is set to "
    f"a value of at least {_MIN_BYTES} bytes"
)


def bi_key_short_warning() -> str:
    return (
        f"SECRET_BI_KEY is shorter than {_MIN_BYTES} bytes ({_MIN_BITS} bits): "
        f"security levels 2 and 3 do not start with it. Set it to a value of "
        f"at least {_MIN_BYTES} bytes. Generate one with: {GENERATE_KEY_HINT}"
    )


def bi_key_short_error(level) -> str:
    return (
        f"Security level {level} requires SECRET_BI_KEY to be at least "
        f"{_MIN_BYTES} bytes ({_MIN_BITS} bits) when it is set: set a longer "
        f"value, or leave it unset (BI tokens are then not available). "
        f"Generate one with: {GENERATE_KEY_HINT}"
    )


def api_key_random_key_warning(user_id) -> str:
    return (
        f"User {user_id} generated a personal API key signed with the random "
        f"secret key of this startup: it stops working when cornflow restarts. "
        f"Set FERNET_KEY to keep API keys valid across restarts."
    )


def cli_api_key_random_key_warning(username) -> str:
    return (
        f"The personal API key for user {username} is signed with a random "
        f"secret key generated by this command, so the server does not accept "
        f"it, and the previous API key of the user has been superseded. Set "
        f"FERNET_KEY to the same value as the server and generate the key again."
    )


EPHEMERAL_KEY_SHARED_INFO = (
    "Neither FERNET_KEY nor SECRET_KEY is set: the random secret key of this "
    f"startup is passed to the gunicorn workers in {EPHEMERAL_SECRET_KEY_ENV_VAR} "
    "so that all of them sign with it. It changes on every restart."
)


def check_secret_keys(
    level: int,
    token_key: Optional[str],
    source: str,
    keys_differ: bool,
    bi_key: Optional[str],
    mfa_enabled: bool,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Returns (warnings, errors). Messages never contain a key value."""
    warnings = []
    errors = []
    strict = level in (2, 3)
    label = (
        source
        if source in (KEY_SOURCE_FERNET_KEY, KEY_SOURCE_SECRET_KEY)
        else "SECRET_TOKEN_KEY"
    )

    if source == KEY_SOURCE_RANDOM:
        if strict:
            errors.append(missing_key_error(level))
        else:
            warnings.append(random_key_warning(mfa_enabled))
    elif source == KEY_SOURCE_MISSING or not token_key:
        if strict:
            errors.append(missing_key_error(level))
        else:
            warnings.append(TOKEN_KEY_MISSING_WARNING)
    elif key_length(token_key) < _MIN_BYTES:
        if strict:
            errors.append(short_key_error(level, label))
        else:
            warnings.append(short_key_warning(label))

    if keys_differ:
        warnings.append(KEYS_DIFFER_WARNING)

    if not bi_key:
        warnings.append(BI_KEY_MISSING_WARNING)
    elif key_length(bi_key) < _MIN_BYTES:
        if strict:
            errors.append(bi_key_short_error(level))
        else:
            warnings.append(bi_key_short_warning())

    return tuple(warnings), tuple(errors)
