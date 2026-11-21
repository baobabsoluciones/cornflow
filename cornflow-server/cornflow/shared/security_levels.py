"""
Security levels: inventory of the security settings and their resolution.

CORNFLOW_SECURITY_LEVEL selects level 1, 2 or 3. Every security setting has a
default value at each level, can be changed with its own environment variable
and may have limits at each level. This module only works on the mapping it
receives (it never reads os.environ nor the Flask application context).
"""

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from cornflow.shared.const import (
    DEFAULT_PWD_HISTORY_SIZE,
    DEFAULT_PWD_MAX_SIMILARITY,
    DEFAULT_PWD_MIN_LENGTH,
    DEFAULT_PWD_MIN_ZXCVBN_SCORE,
    DEFAULT_PWD_ROTATION_TIME,
    SIGNUP_PLATFORM_ADMIN_ONLY,
    SIGNUP_WITH_AUTH,
)

SECURITY_LEVEL_ENV_VAR = "CORNFLOW_SECURITY_LEVEL"
SECURITY_LEVELS = (1, 2, 3)
DEFAULT_SECURITY_LEVEL = 1

# Key variables: no default value, resolved elsewhere. Not part of SECURITY_SETTINGS.
SECRET_KEY_ENV_VARS = ("FERNET_KEY", "SECRET_KEY", "SECRET_BI_KEY")

# Value kinds
KIND_INT = "int"
KIND_FLOAT = "float"
KIND_STR = "str"  # taken verbatim from the environment, "" included
KIND_OPTIONAL_STR = "optional_str"  # same, but the default is None

# Reasons of an adjustment
ADJUSTED_TO_MINIMUM = "minimum"
ADJUSTED_TO_MAXIMUM = "maximum"
INVALID_VALUE = "invalid"

# app.config keys with the resolution metadata
CONFIG_KEY_LEVEL = "SECURITY_LEVEL"
CONFIG_KEY_LEVEL_ERROR = "SECURITY_LEVEL_ERROR"
CONFIG_KEY_ERRORS = "SECURITY_CONFIG_ERRORS"
CONFIG_KEY_CHANGED = "SECURITY_CHANGED_SETTINGS"
CONFIG_KEY_ADJUSTED = "SECURITY_ADJUSTED_SETTINGS"
METADATA_CONFIG_KEYS = (
    CONFIG_KEY_LEVEL,
    CONFIG_KEY_LEVEL_ERROR,
    CONFIG_KEY_ERRORS,
    CONFIG_KEY_CHANGED,
    CONFIG_KEY_ADJUSTED,
)

_VALID_KINDS = (KIND_INT, KIND_FLOAT, KIND_STR, KIND_OPTIONAL_STR)
_TEXT_KINDS = (KIND_STR, KIND_OPTIONAL_STR)


@dataclass(frozen=True)
class Bounds:
    """Inclusive limits of a numeric setting at one level. None means no limit."""

    minimum: Optional[float] = None
    maximum: Optional[float] = None


NO_BOUNDS = Bounds()


@dataclass(frozen=True)
class SecuritySetting:
    env_var: str  # environment variable, e.g. "CORNFLOW_DOCS_ENABLED"
    config_key: str  # app.config key, e.g. "DOCS_ENABLED"
    kind: str  # KIND_INT | KIND_FLOAT | KIND_STR | KIND_OPTIONAL_STR
    defaults: Tuple[Any, Any, Any]  # default value at levels 1, 2 and 3
    bounds: Tuple[Bounds, Bounds, Bounds] = (NO_BOUNDS, NO_BOUNDS, NO_BOUNDS)
    zero_disables: Optional[str] = None  # what a value <= 0 turns off
    original_scope: bool = True  # False: outside the original scope of the change
    sensitive: bool = False  # the effective value must never be logged
    description: str = ""

    def __post_init__(self):
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"{self.env_var}: unknown kind {self.kind!r}")
        if len(self.defaults) != 3:
            raise ValueError(f"{self.env_var}: defaults must have 3 elements")
        if len(self.bounds) != 3:
            raise ValueError(f"{self.env_var}: bounds must have 3 elements")
        if self.kind != KIND_OPTIONAL_STR and any(d is None for d in self.defaults):
            raise ValueError(f"{self.env_var}: only optional_str can default to None")
        if self.kind in _TEXT_KINDS and (
            any(b != NO_BOUNDS for b in self.bounds) or self.zero_disables
        ):
            raise ValueError(f"{self.env_var}: text settings have no limits")

    def default_for(self, level: int) -> Any:
        return self.defaults[level - 1]

    def bounds_for(self, level: int) -> Bounds:
        return self.bounds[level - 1]


def _text(value: Any) -> str:
    return "unset" if value is None else str(value)


@dataclass(frozen=True)
class SettingChange:
    """A defined variable whose effective value differs from the level default."""

    env_var: str
    config_key: str
    level_default: Any
    effective: Any
    sensitive: bool = False

    def as_log_text(self) -> str:
        if self.sensitive:
            effective = "value set (hidden)"
        else:
            effective = _text(self.effective)
        return (
            f"{self.config_key}: level default {_text(self.level_default)}, "
            f"effective {effective}"
        )


@dataclass(frozen=True)
class SettingAdjustment:
    """A defined numeric variable that was clamped to a limit or could not be parsed."""

    env_var: str
    config_key: str
    requested: str  # raw value as found in the environment
    applied: Any  # value finally used
    reason: str  # ADJUSTED_TO_MINIMUM | ADJUSTED_TO_MAXIMUM | INVALID_VALUE
    level: int

    def as_log_text(self) -> str:
        if self.reason == INVALID_VALUE:
            return (
                f"{self.config_key}: requested {self.requested!r} is not a valid "
                f"{type(self.applied).__name__}, applied the level default "
                f"{self.applied}"
            )
        return (
            f"{self.config_key}: requested {self.requested!r}, applied "
            f"{self.applied} ({self.reason} allowed at security level {self.level})"
        )


@dataclass(frozen=True)
class ResolvedSecuritySettings:
    level: int  # effective level; 1 (provisional) when level_error is set
    level_error: Optional[str]  # message for an invalid level, else None
    errors: Tuple[str, ...]  # messages of a disabling zero not allowed
    values: Mapping[str, Any]  # config_key -> effective value (read-only)
    changed: Tuple[SettingChange, ...]
    adjusted: Tuple[SettingAdjustment, ...]

    @property
    def all_errors(self) -> Tuple[str, ...]:
        """level_error (if any) followed by errors."""
        if self.level_error is None:
            return tuple(self.errors)
        return (self.level_error,) + tuple(self.errors)


def _b(l1=None, l2=None, l3=None) -> Tuple[Bounds, Bounds, Bounds]:
    """Builds the bounds of the three levels from (minimum, maximum) pairs."""
    return tuple(  # type: ignore[return-value]
        NO_BOUNDS if pair is None else Bounds(*pair) for pair in (l1, l2, l3)
    )


def _s(env_var, kind, defaults, description, config_key=None, **kwargs):
    return SecuritySetting(
        env_var=env_var,
        config_key=config_key or env_var,
        kind=kind,
        defaults=tuple(defaults),
        description=description,
        **kwargs,
    )


def _same(value):
    return (value, value, value)


_OUT = {"original_scope": False}

SECURITY_SETTINGS: Tuple[SecuritySetting, ...] = (
    _s("BCRYPT_LOG_ROUNDS", KIND_INT, _same(12),
       "bcrypt work factor for password hashing (CCN-STIC-807 minimum of 12).",
       bounds=_b((12, None), (12, None), (12, None))),
    _s("AUDIT_LOG_ENABLED", KIND_INT, _same(1),
       "Emit security events as JSON lines on the cornflow.audit logger."),
    _s("SECURITY_HEADERS_ENABLED", KIND_INT, _same(1),
       "Stamp the HTTP security headers on every response (browsers only)."),
    _s("RATELIMIT_ENABLED", KIND_INT, _same(1),
       "Per-IP rate limiting of the sensitive unauthenticated endpoints."),
    _s("RATELIMIT_LOGIN", KIND_STR, _same("10 per minute"),
       "Rate limit of the login endpoint."),
    _s("RATELIMIT_RECOVER", KIND_STR, _same("5 per hour"),
       "Rate limit of the password recovery endpoint."),
    _s("RATELIMIT_TRUST_FORWARDED_FOR", KIND_INT, _same(0),
       "Trust the X-Forwarded-For header; only behind a trusted reverse proxy."),
    _s("PLATFORM_DATA_ISOLATION", KIND_INT, _same(1),
       "Objects created by platform-role users are invisible to client users."),
    _s("PERSONAL_TOKEN_ENABLED", KIND_INT, _same(1),
       "Allow personal API key generation; 0 disables it."),
    _s("CORNFLOW_UI_URL", KIND_OPTIONAL_STR, _same(None),
       "Base URL of the cornflow web client, used for the password reset link; "
       "when unset the recovery email sends a temporary password."),
    _s("MFA_ENABLED", KIND_INT, (0, 0, 1),
       "Offer TOTP multi-factor authentication endpoints."),
    _s("MFA_REQUIRED", KIND_INT, (0, 0, 1),
       "All internal users except service users must enroll and use a TOTP code."),
    _s("API_KEY_STEPUP_TOTP", KIND_INT, (0, 0, 1),
       "Require a fresh TOTP code to generate an API key through the API."),
    _s("PLATFORM_ROLE_STEPUP_TOTP", KIND_INT, (0, 0, 1),
       "Require a fresh TOTP code from the administrator to grant a platform role."),
    _s("REFRESH_TOKEN_ENABLED", KIND_INT, (0, 0, 1),
       "Interactive logins return an access token plus a refresh token."),
    _s("TOKEN_DURATION", KIND_FLOAT, (24.0, 8.0, 8.0),
       "Lifetime in hours of the single session token (levels 1 and 2, "
       "service users and fallback).",
       bounds=_b(None, (None, 24.0), (None, 24.0))),
    _s("ACCESS_TOKEN_DURATION_MINUTES", KIND_INT, _same(15),
       "Lifetime in minutes of the access token.",
       bounds=_b(None, None, (None, 60))),
    _s("REFRESH_TOKEN_INACTIVITY_MINUTES", KIND_INT, _same(30),
       "Sliding inactivity window in minutes after which a session is closed.",
       bounds=_b(None, None, (None, 720))),
    _s("REFRESH_TOKEN_ABSOLUTE_HOURS", KIND_INT, _same(12),
       "Absolute maximum session lifetime in hours.",
       bounds=_b(None, None, (None, 24))),
    _s("PWD_MIN_LENGTH", KIND_INT, (5, DEFAULT_PWD_MIN_LENGTH, DEFAULT_PWD_MIN_LENGTH),
       "Minimum password length.",
       bounds=_b(None, (DEFAULT_PWD_MIN_LENGTH, None), (DEFAULT_PWD_MIN_LENGTH, None))),
    _s("PWD_MIN_ZXCVBN_SCORE", KIND_INT,
       (0, DEFAULT_PWD_MIN_ZXCVBN_SCORE, DEFAULT_PWD_MIN_ZXCVBN_SCORE),
       "Minimum zxcvbn strength score (0-4) of new passwords.",
       bounds=_b(None, (DEFAULT_PWD_MIN_ZXCVBN_SCORE, None),
                 (DEFAULT_PWD_MIN_ZXCVBN_SCORE, None))),
    _s("PWD_HISTORY_SIZE", KIND_INT, _same(DEFAULT_PWD_HISTORY_SIZE),
       "Number of previous passwords that can not be reused.",
       bounds=_b(None, (DEFAULT_PWD_HISTORY_SIZE, None),
                 (DEFAULT_PWD_HISTORY_SIZE, None))),
    _s("PWD_MAX_SIMILARITY", KIND_FLOAT, _same(DEFAULT_PWD_MAX_SIMILARITY),
       "Similarity ratio (0-1) above which a new password is rejected for being "
       "too close to the previous one.",
       bounds=_b(None, (None, 0.9), (None, 0.9))),
    _s("PWD_ROTATION_ENFORCE", KIND_INT, (0, 0, 1),
       "Users with an expired or flagged password can only change it."),
    _s("PWD_ROTATION_TIME", KIND_INT, _same(DEFAULT_PWD_ROTATION_TIME),
       "Password rotation time in days.",
       bounds=_b(None, None, (None, 365))),
    _s("LOGIN_MAX_ATTEMPTS", KIND_INT, (0, 5, 5),
       "Consecutive failed logins that lock an account; 0 disables lockout "
       "(level 1 only).",
       bounds=_b(None, (1, 10), (1, 10)), zero_disables="account lockout"),
    _s("SIGNUP_ACTIVATED", KIND_INT, (SIGNUP_WITH_AUTH, SIGNUP_PLATFORM_ADMIN_ONLY,
                                      SIGNUP_PLATFORM_ADMIN_ONLY),
       "Who can sign up new users."),
    _s("BI_TOKEN_DURATION_DAYS", KIND_INT, (0, 0, 90),
       "Lifetime in days of BI tokens; 0 means they never expire "
       "(levels 1 and 2 only).",
       bounds=_b(None, None, (1, 365)), zero_disables="BI token expiry"),
    _s("API_KEY_DURATION_DAYS", KIND_INT, _same(365),
       "Lifetime in days of personal API keys.",
       bounds=_b(None, None, (None, 730))),
    _s("API_KEY_ROTATION_GRACE_MINUTES", KIND_INT, _same(60),
       "Minutes the previous API key keeps working after generating a new one.",
       bounds=_b(None, None, (None, 1440))),
    _s("MFA_SETUP_TOKEN_DURATION_MINUTES", KIND_INT, _same(10),
       "Lifetime in minutes of the temporary token issued to enroll in MFA.",
       bounds=_b(None, None, (None, 30))),
    _s("PWD_RESET_TOKEN_DURATION_MINUTES", KIND_INT, _same(30),
       "Lifetime in minutes of the password reset link.",
       bounds=_b(None, None, (None, 60))),
    _s("MFA_BACKUP_CODES_NUMBER", KIND_INT, _same(8),
       "Number of one-time backup codes generated on MFA enrollment.",
       bounds=_b(None, None, (None, 20))),
    _s("CORS_ORIGINS", KIND_STR, ("*", "*", ""),
       "Allowed cross-origin origins; empty means closed."),
    _s("CORNFLOW_DOCS_ENABLED", KIND_INT, (1, 1, 0),
       "Serve the interactive API docs (Swagger UI).", config_key="DOCS_ENABLED"),
    _s("HSTS_ENABLED", KIND_INT, (0, 0, 1),
       "Send the HSTS header; enable it only once TLS terminates in front of cornflow."),
    _s("CONTENT_SECURITY_POLICY", KIND_OPTIONAL_STR, _same(None),
       "Override of the Content-Security-Policy header; unset uses the strict default.",
       **_OUT),
    _s("PERMISSIONS_POLICY", KIND_OPTIONAL_STR, _same(None),
       "Override of the Permissions-Policy header; unset uses the strict default.",
       **_OUT),
    _s("REFERRER_POLICY", KIND_OPTIONAL_STR, _same(None),
       "Override of the Referrer-Policy header; unset uses the strict default.",
       **_OUT),
    _s("SECURITY_NO_STORE", KIND_INT, _same(1),
       "Ask browsers and proxies not to cache responses.", **_OUT),
    _s("HSTS_MAX_AGE", KIND_INT, _same(31536000),
       "max-age in seconds of the HSTS header.", **_OUT),
    _s("HSTS_INCLUDE_SUBDOMAINS", KIND_INT, _same(1),
       "Add includeSubDomains to the HSTS header.", **_OUT),
    _s("HSTS_PRELOAD", KIND_INT, _same(0),
       "Add preload to the HSTS header.", **_OUT),
    _s("RATELIMIT_STORAGE_URI", KIND_STR, _same("memory://"),
       "Storage of the rate limit counters; the in-memory default is per process, "
       "so several workers should use a shared backend such as redis://host:6379.",
       sensitive=True, **_OUT),
    _s("SERVICE_USER_ALLOW_PASSWORD_LOGIN", KIND_INT, _same(1),
       "Service users may log in with username and password.", **_OUT),
    _s("TOKEN_EXPIRY_NOTIFICATIONS_ENABLED", KIND_INT, _same(1),
       "Email the owner and the administrators when an API key is about to expire.",
       **_OUT),
    _s("TOKEN_EXPIRY_NOTIFICATION_DAYS", KIND_STR, _same("30,7,3,2,1"),
       "Comma separated days left that trigger an API key expiry notification.",
       **_OUT),
)

SETTINGS_BY_ENV_VAR: Mapping[str, SecuritySetting] = MappingProxyType(
    {s.env_var: s for s in SECURITY_SETTINGS}
)
SETTINGS_BY_CONFIG_KEY: Mapping[str, SecuritySetting] = MappingProxyType(
    {s.config_key: s for s in SECURITY_SETTINGS}
)


def parse_security_level(raw: Optional[str]) -> Tuple[int, Optional[str]]:
    """
    Returns (level, error). None gives (1, None); "1", "2" or "3" (spaces
    allowed around) give (level, None); anything else gives (1, message).
    """
    if raw is None:
        return DEFAULT_SECURITY_LEVEL, None
    text = raw.strip()
    if text in ("1", "2", "3"):
        return int(text), None
    return (
        DEFAULT_SECURITY_LEVEL,
        f"{SECURITY_LEVEL_ENV_VAR} must be 1, 2 or 3 (got {raw!r})",
    )


def _parse_number(text: str, kind: str):
    """Parses a numeric value; raises ValueError if it is not valid."""
    if kind == KIND_INT:
        return int(text)
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(text)
    return value


def _cast(value: Any, kind: str):
    return int(value) if kind == KIND_INT else float(value)


def _disabling_zero_message(setting, level, parsed, bounds) -> str:
    return (
        f"{setting.env_var}={parsed} turns off {setting.zero_disables}, which "
        f"security level {level} does not allow: set a value between "
        f"{int(bounds.minimum)} and {int(bounds.maximum)}, or leave it unset to "
        f"use the level default ({int(setting.default_for(level))})"
    )


def resolve_security_settings(environ: Mapping[str, str]) -> ResolvedSecuritySettings:
    """
    Pure: resolves the level and the settings from the given mapping. Never
    raises because of the values found in it, never reads os.environ and never
    mutates environ.
    """
    level, level_error = parse_security_level(environ.get(SECURITY_LEVEL_ENV_VAR))
    values: Dict[str, Any] = {}
    errors, changed, adjusted = [], [], []

    for setting in SECURITY_SETTINGS:
        key = setting.config_key
        default = setting.default_for(level)
        raw = environ.get(setting.env_var)
        if raw is None:
            values[key] = default
            continue

        if setting.kind in _TEXT_KINDS:
            value = raw
        else:
            text = raw.strip()
            if text == "":
                values[key] = default
                continue
            try:
                parsed = _parse_number(text, setting.kind)
            except ValueError:
                value = default
                adjusted.append(
                    SettingAdjustment(
                        setting.env_var, key, raw, value, INVALID_VALUE, level
                    )
                )
            else:
                bounds = setting.bounds_for(level)
                if (
                    setting.zero_disables
                    and level_error is None
                    and bounds.minimum is not None
                    and bounds.minimum > 0
                    and parsed <= 0
                ):
                    value = default
                    errors.append(
                        _disabling_zero_message(setting, level, parsed, bounds)
                    )
                elif bounds.minimum is not None and parsed < bounds.minimum:
                    value = _cast(bounds.minimum, setting.kind)
                    adjusted.append(
                        SettingAdjustment(
                            setting.env_var, key, raw, value, ADJUSTED_TO_MINIMUM, level
                        )
                    )
                elif bounds.maximum is not None and parsed > bounds.maximum:
                    value = _cast(bounds.maximum, setting.kind)
                    adjusted.append(
                        SettingAdjustment(
                            setting.env_var, key, raw, value, ADJUSTED_TO_MAXIMUM, level
                        )
                    )
                else:
                    value = parsed

        values[key] = value
        if value != default:
            changed.append(
                SettingChange(setting.env_var, key, default, value, setting.sensitive)
            )

    return ResolvedSecuritySettings(
        level,
        level_error,
        tuple(errors),
        MappingProxyType(values),
        tuple(changed),
        tuple(adjusted),
    )


def default_values(level: int) -> Dict[str, Any]:
    """config_key -> default value of the level. ValueError for an unknown level."""
    if isinstance(level, bool) or level not in SECURITY_LEVELS:
        raise ValueError(f"Unknown security level {level!r}")
    return {s.config_key: s.default_for(level) for s in SECURITY_SETTINGS}


def apply_security_settings(config_class: type, resolved: ResolvedSecuritySettings) -> type:
    """
    Sets on config_class every resolved value whose config_key is not declared
    in config_class.__dict__ (the class body wins), plus the five metadata
    keys (always). Returns the same class.
    """
    for key, value in resolved.values.items():
        if key not in config_class.__dict__:
            setattr(config_class, key, value)
    setattr(config_class, CONFIG_KEY_LEVEL, resolved.level)
    setattr(config_class, CONFIG_KEY_LEVEL_ERROR, resolved.level_error)
    setattr(config_class, CONFIG_KEY_ERRORS, resolved.errors)
    setattr(config_class, CONFIG_KEY_CHANGED, resolved.changed)
    setattr(config_class, CONFIG_KEY_ADJUSTED, resolved.adjusted)
    return config_class
