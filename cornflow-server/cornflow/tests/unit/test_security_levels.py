"""
Tests for the security levels (CORNFLOW_SECURITY_LEVEL): selector, inventory of
default values and limits per level, resolution of the environment, the
configuration classes and the per-level test helper.

The expected values are written in this file on purpose (they come from the
tables of the plan, not from the inventory under test), so a wrong entry of the
inventory makes a test fail instead of being copied to the expectations.

``cornflow.config`` is never reloaded: the pure resolution is tested with
mappings and the real reading of ``os.environ`` is tested in a subprocess.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import jwt
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.commands.access import access_init_command
from cornflow.config import (
    Development,
    Production,
    Testing,
    TestingApplicationRoot,
    TestingDatabricks,
    TestingOpenAuth,
    TestingRateLimit,
    app_config,
)
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import PLANNER_ROLE
from cornflow.shared.security_levels import (
    ADJUSTED_TO_MAXIMUM,
    ADJUSTED_TO_MINIMUM,
    INVALID_VALUE,
    KIND_OPTIONAL_STR,
    METADATA_CONFIG_KEYS,
    SECRET_KEY_ENV_VARS,
    SECURITY_LEVEL_ENV_VAR,
    SECURITY_SETTINGS,
    SETTINGS_BY_ENV_VAR,
    SettingAdjustment,
    SettingChange,
    apply_security_settings,
    default_values,
    parse_security_level,
    resolve_security_settings,
)
from cornflow.tests.const import LOGIN_URL
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    build_security_level_config,
    security_level_config,
)

LEVELS = (1, 2, 3)
PASSWORD = "Kx9#tR2m!Qw7Zp"

# ---------------------------------------------------------------------------
# Expected data (tables 4.2 and 4.3 of the plan)
# ---------------------------------------------------------------------------

# env var -> (level 1, level 2, level 3)
EXPECTED_DEFAULTS = {
    "BCRYPT_LOG_ROUNDS": (12, 12, 12),
    "AUDIT_LOG_ENABLED": (1, 1, 1),
    "SECURITY_HEADERS_ENABLED": (1, 1, 1),
    "RATELIMIT_ENABLED": (1, 1, 1),
    "RATELIMIT_LOGIN": ("10 per minute",) * 3,
    "RATELIMIT_RECOVER": ("5 per hour",) * 3,
    "RATELIMIT_TRUST_FORWARDED_FOR": (0, 0, 0),
    "PLATFORM_DATA_ISOLATION": (1, 1, 1),
    "PERSONAL_TOKEN_ENABLED": (1, 1, 1),
    "CORNFLOW_UI_URL": (None, None, None),
    "MFA_ENABLED": (0, 0, 1),
    "MFA_REQUIRED": (0, 0, 1),
    "API_KEY_STEPUP_TOTP": (0, 0, 1),
    "PLATFORM_ROLE_STEPUP_TOTP": (0, 0, 1),
    "REFRESH_TOKEN_ENABLED": (0, 0, 1),
    "TOKEN_DURATION": (24.0, 8.0, 8.0),
    "ACCESS_TOKEN_DURATION_MINUTES": (15, 15, 15),
    "REFRESH_TOKEN_INACTIVITY_MINUTES": (30, 30, 30),
    "REFRESH_TOKEN_ABSOLUTE_HOURS": (12, 12, 12),
    "PWD_MIN_LENGTH": (5, 12, 12),
    "PWD_MIN_ZXCVBN_SCORE": (0, 3, 3),
    "PWD_HISTORY_SIZE": (10, 10, 10),
    "PWD_MAX_SIMILARITY": (0.8, 0.8, 0.8),
    "PWD_ROTATION_ENFORCE": (0, 0, 1),
    "PWD_ROTATION_TIME": (120, 120, 120),
    "LOGIN_MAX_ATTEMPTS": (0, 5, 5),
    "SIGNUP_ACTIVATED": (2, 3, 3),
    "BI_TOKEN_DURATION_DAYS": (0, 0, 90),
    "API_KEY_DURATION_DAYS": (365, 365, 365),
    "API_KEY_ROTATION_GRACE_MINUTES": (60, 60, 60),
    "MFA_SETUP_TOKEN_DURATION_MINUTES": (10, 10, 10),
    "PWD_RESET_TOKEN_DURATION_MINUTES": (30, 30, 30),
    "MFA_BACKUP_CODES_NUMBER": (8, 8, 8),
    "CORS_ORIGINS": ("*", "*", ""),
    "CORNFLOW_DOCS_ENABLED": (1, 1, 0),
    "HSTS_ENABLED": (0, 0, 1),
    "CONTENT_SECURITY_POLICY": (None, None, None),
    "PERMISSIONS_POLICY": (None, None, None),
    "REFERRER_POLICY": (None, None, None),
    "SECURITY_NO_STORE": (1, 1, 1),
    "HSTS_MAX_AGE": (31536000, 31536000, 31536000),
    "HSTS_INCLUDE_SUBDOMAINS": (1, 1, 1),
    "HSTS_PRELOAD": (0, 0, 0),
    "RATELIMIT_STORAGE_URI": ("memory://",) * 3,
    "SERVICE_USER_ALLOW_PASSWORD_LOGIN": (1, 1, 1),
    "TOKEN_EXPIRY_NOTIFICATIONS_ENABLED": (1, 1, 1),
    "TOKEN_EXPIRY_NOTIFICATION_DAYS": ("30,7,3,2,1",) * 3,
}

# env var -> {level: (minimum, maximum)}; only the limits that exist
_BCRYPT = (12, None)
EXPECTED_BOUNDS = {
    "BCRYPT_LOG_ROUNDS": {1: _BCRYPT, 2: _BCRYPT, 3: _BCRYPT},
    "TOKEN_DURATION": {2: (None, 24.0), 3: (None, 24.0)},
    "ACCESS_TOKEN_DURATION_MINUTES": {3: (None, 60)},
    "REFRESH_TOKEN_INACTIVITY_MINUTES": {3: (None, 720)},
    "REFRESH_TOKEN_ABSOLUTE_HOURS": {3: (None, 24)},
    "PWD_MIN_LENGTH": {2: (12, None), 3: (12, None)},
    "PWD_MIN_ZXCVBN_SCORE": {2: (3, None), 3: (3, None)},
    "PWD_HISTORY_SIZE": {2: (10, None), 3: (10, None)},
    "PWD_MAX_SIMILARITY": {2: (None, 0.9), 3: (None, 0.9)},
    "PWD_ROTATION_TIME": {3: (None, 365)},
    "LOGIN_MAX_ATTEMPTS": {2: (1, 10), 3: (1, 10)},
    "BI_TOKEN_DURATION_DAYS": {3: (1, 365)},
    "API_KEY_DURATION_DAYS": {3: (None, 730)},
    "API_KEY_ROTATION_GRACE_MINUTES": {3: (None, 1440)},
    "MFA_SETUP_TOKEN_DURATION_MINUTES": {3: (None, 30)},
    "PWD_RESET_TOKEN_DURATION_MINUTES": {3: (None, 60)},
    "MFA_BACKUP_CODES_NUMBER": {3: (None, 20)},
}

EXPECTED_CONFIG_KEYS = {
    env_var: ("DOCS_ENABLED" if env_var == "CORNFLOW_DOCS_ENABLED" else env_var)
    for env_var in EXPECTED_DEFAULTS
}

FLOAT_VARS = {"TOKEN_DURATION", "PWD_MAX_SIMILARITY"}
STR_VARS = {
    "RATELIMIT_LOGIN",
    "RATELIMIT_RECOVER",
    "CORS_ORIGINS",
    "RATELIMIT_STORAGE_URI",
    "TOKEN_EXPIRY_NOTIFICATION_DAYS",
}
OPTIONAL_STR_VARS = {
    "CORNFLOW_UI_URL",
    "CONTENT_SECURITY_POLICY",
    "PERMISSIONS_POLICY",
    "REFERRER_POLICY",
}
NUMERIC_VARS = sorted(set(EXPECTED_DEFAULTS) - STR_VARS - OPTIONAL_STR_VARS)

SWITCHES = {
    "MFA_ENABLED",
    "MFA_REQUIRED",
    "REFRESH_TOKEN_ENABLED",
    "PWD_ROTATION_ENFORCE",
    "API_KEY_STEPUP_TOTP",
    "PLATFORM_ROLE_STEPUP_TOTP",
    "SIGNUP_ACTIVATED",
    "CORS_ORIGINS",
    "CORNFLOW_DOCS_ENABLED",
    "HSTS_ENABLED",
    "RATELIMIT_ENABLED",
    "AUDIT_LOG_ENABLED",
    "SECURITY_HEADERS_ENABLED",
    "PERSONAL_TOKEN_ENABLED",
    "PLATFORM_DATA_ISOLATION",
}

OUTSIDE_ORIGINAL_SCOPE = {
    "CONTENT_SECURITY_POLICY",
    "PERMISSIONS_POLICY",
    "REFERRER_POLICY",
    "SECURITY_NO_STORE",
    "HSTS_MAX_AGE",
    "HSTS_INCLUDE_SUBDOMAINS",
    "HSTS_PRELOAD",
    "RATELIMIT_STORAGE_URI",
    "SERVICE_USER_ALLOW_PASSWORD_LOGIN",
    "TOKEN_EXPIRY_NOTIFICATIONS_ENABLED",
    "TOKEN_EXPIRY_NOTIFICATION_DAYS",
}

# 0/1 flags that are inverted with respect to the default of the level
_FLAGS_TO_INVERT = (SWITCHES - {"SIGNUP_ACTIVATED", "CORS_ORIGINS"}) | {
    "RATELIMIT_TRUST_FORWARDED_FOR",
    "SECURITY_NO_STORE",
    "HSTS_INCLUDE_SUBDOMAINS",
    "HSTS_PRELOAD",
    "SERVICE_USER_ALLOW_PASSWORD_LOGIN",
    "TOKEN_EXPIRY_NOTIFICATIONS_ENABLED",
}

# Valid value (environment string) in the three levels, different from the
# default of every level
VALID_ALTERNATIVES = {
    "BCRYPT_LOG_ROUNDS": "13",
    "TOKEN_DURATION": "12",
    "ACCESS_TOKEN_DURATION_MINUTES": "20",
    "REFRESH_TOKEN_INACTIVITY_MINUTES": "60",
    "REFRESH_TOKEN_ABSOLUTE_HOURS": "10",
    "PWD_MIN_LENGTH": "14",
    "PWD_MIN_ZXCVBN_SCORE": "4",
    "PWD_HISTORY_SIZE": "12",
    "PWD_MAX_SIMILARITY": "0.7",
    "PWD_ROTATION_TIME": "90",
    "LOGIN_MAX_ATTEMPTS": "3",
    "SIGNUP_ACTIVATED": "1",
    "BI_TOKEN_DURATION_DAYS": "30",
    "API_KEY_DURATION_DAYS": "180",
    "API_KEY_ROTATION_GRACE_MINUTES": "30",
    "MFA_SETUP_TOKEN_DURATION_MINUTES": "5",
    "PWD_RESET_TOKEN_DURATION_MINUTES": "15",
    "MFA_BACKUP_CODES_NUMBER": "10",
    "HSTS_MAX_AGE": "600",
    "CORS_ORIGINS": "https://ui.example.com",
    "RATELIMIT_LOGIN": "20 per minute",
    "RATELIMIT_RECOVER": "3 per hour",
    "RATELIMIT_STORAGE_URI": "redis://cache:6379/0",
    "TOKEN_EXPIRY_NOTIFICATION_DAYS": "14,1",
    "CONTENT_SECURITY_POLICY": "default-src 'self'",
    "PERMISSIONS_POLICY": "camera=()",
    "REFERRER_POLICY": "same-origin",
    "CORNFLOW_UI_URL": "https://ui.example.com",
}

DISABLING_ZERO_VARS = {"LOGIN_MAX_ATTEMPTS", "BI_TOKEN_DURATION_DAYS"}

LOGIN_LOCKOUT_MESSAGE = (
    "LOGIN_MAX_ATTEMPTS={value} turns off account lockout, which security "
    "level {level} does not allow: set a value between 1 and 10, or leave it "
    "unset to use the level default (5)"
)
BI_EXPIRY_MESSAGE = (
    "BI_TOKEN_DURATION_DAYS={value} turns off BI token expiry, which security "
    "level {level} does not allow: set a value between 1 and 365, or leave it "
    "unset to use the level default (90)"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def convert(env_var, raw):
    """Converts an environment string to the type of the setting."""
    if env_var in STR_VARS or env_var in OPTIONAL_STR_VARS:
        return raw
    if env_var in FLOAT_VARS:
        return float(raw)
    return int(raw)


def expected_default(env_var, level):
    return EXPECTED_DEFAULTS[env_var][level - 1]


def alternative_for(env_var, level):
    if env_var in VALID_ALTERNATIVES:
        return VALID_ALTERNATIVES[env_var]
    return str(1 - expected_default(env_var, level))


def resolve(level, **env):
    """Resolves a level (None leaves the selector unset) plus raw variables."""
    environ = {}
    if level is not None:
        environ[SECURITY_LEVEL_ENV_VAR] = str(level)
    environ.update(env)
    return resolve_security_settings(environ)


def by_env_var(entries):
    return {entry.env_var: entry for entry in entries}


def expected_values(level):
    return {
        EXPECTED_CONFIG_KEYS[env_var]: expected_default(env_var, level)
        for env_var in EXPECTED_DEFAULTS
    }


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


class TestSecurityLevelSelector(unittest.TestCase):
    def test_unset_level_is_1(self):
        resolved = resolve_security_settings({})
        self.assertEqual(1, resolved.level)
        self.assertIsNone(resolved.level_error)
        self.assertEqual((), resolved.errors)
        self.assertEqual(expected_values(1), dict(resolved.values))

    def test_valid_levels(self):
        for raw, level in (("1", 1), ("2", 2), ("3", 3), (" 2 ", 2), ("3\n", 3)):
            with self.subTest(raw=raw):
                resolved = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: raw})
                self.assertEqual(level, resolved.level)
                self.assertIs(int, type(resolved.level))
                self.assertIsNone(resolved.level_error)
                self.assertEqual((), resolved.all_errors)

    def test_invalid_levels_register_an_error(self):
        for raw in ("4", "0", "-1", "abc", "", "   ", "1.5", "02", "+2"):
            with self.subTest(raw=raw):
                resolved = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: raw})
                self.assertEqual(1, resolved.level)
                self.assertEqual(
                    f"CORNFLOW_SECURITY_LEVEL must be 1, 2 or 3 (got {raw!r})",
                    resolved.level_error,
                )
                self.assertEqual(expected_values(1), dict(resolved.values))
                self.assertEqual((resolved.level_error,), resolved.all_errors)

    def test_parse_security_level(self):
        self.assertEqual((1, None), parse_security_level(None))
        self.assertEqual((3, None), parse_security_level(" 3 "))
        level, error = parse_security_level("x")
        self.assertEqual(1, level)
        self.assertEqual("CORNFLOW_SECURITY_LEVEL must be 1, 2 or 3 (got 'x')", error)

    def test_invalid_level_skips_disabling_zero_check(self):
        resolved = resolve_security_settings(
            {SECURITY_LEVEL_ENV_VAR: "abc", "LOGIN_MAX_ATTEMPTS": "0"}
        )
        self.assertIsNotNone(resolved.level_error)
        self.assertEqual((), resolved.errors)
        self.assertEqual(0, resolved.values["LOGIN_MAX_ATTEMPTS"])


# ---------------------------------------------------------------------------
# Inventory and resolution
# ---------------------------------------------------------------------------


class TestSecurityInventory(unittest.TestCase):
    def test_inventory_has_the_47_variables(self):
        self.assertEqual(47, len(EXPECTED_DEFAULTS))
        self.assertEqual(47, len(SECURITY_SETTINGS))
        env_vars = [setting.env_var for setting in SECURITY_SETTINGS]
        config_keys = [setting.config_key for setting in SECURITY_SETTINGS]
        self.assertEqual(47, len(set(env_vars)))
        self.assertEqual(47, len(set(config_keys)))
        self.assertEqual(set(EXPECTED_DEFAULTS), set(env_vars))
        for setting in SECURITY_SETTINGS:
            with self.subTest(env_var=setting.env_var):
                self.assertEqual(
                    EXPECTED_CONFIG_KEYS[setting.env_var], setting.config_key
                )

    def test_every_setting_has_a_default_per_level(self):
        for setting in SECURITY_SETTINGS:
            with self.subTest(env_var=setting.env_var):
                self.assertEqual(3, len(setting.defaults))
                self.assertEqual(3, len(setting.bounds))
                for level in LEVELS:
                    if setting.default_for(level) is None:
                        self.assertEqual(KIND_OPTIONAL_STR, setting.kind)

    def test_defaults_match_the_plan(self):
        for level in LEVELS:
            defaults = default_values(level)
            self.assertEqual(47, len(defaults))
            for env_var in EXPECTED_DEFAULTS:
                with self.subTest(level=level, env_var=env_var):
                    expected = expected_default(env_var, level)
                    setting = SETTINGS_BY_ENV_VAR[env_var]
                    key = EXPECTED_CONFIG_KEYS[env_var]
                    for actual in (setting.default_for(level), defaults[key]):
                        self.assertEqual(expected, actual)
                        self.assertIs(type(expected), type(actual))

    def test_default_values_rejects_an_unknown_level(self):
        for level in (0, 4, "1", None):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):
                    default_values(level)

    def test_bounds_match_the_plan(self):
        for level in LEVELS:
            for env_var in EXPECTED_DEFAULTS:
                with self.subTest(level=level, env_var=env_var):
                    bounds = SETTINGS_BY_ENV_VAR[env_var].bounds_for(level)
                    expected = EXPECTED_BOUNDS.get(env_var, {}).get(level, (None, None))
                    self.assertEqual(expected, (bounds.minimum, bounds.maximum))

    def test_bounds_counts_per_level(self):
        for level, count in ((1, 1), (2, 7), (3, 17)):
            with self.subTest(level=level):
                limited = [
                    env_var
                    for env_var in EXPECTED_DEFAULTS
                    if level in EXPECTED_BOUNDS.get(env_var, {})
                ]
                self.assertEqual(count, len(limited))
                actual = [
                    setting.env_var
                    for setting in SECURITY_SETTINGS
                    if setting.bounds_for(level).minimum is not None
                    or setting.bounds_for(level).maximum is not None
                ]
                self.assertEqual(count, len(actual))

    def test_switches_have_no_bounds(self):
        self.assertEqual(15, len(SWITCHES))
        for env_var in SWITCHES:
            for level in LEVELS:
                with self.subTest(env_var=env_var, level=level):
                    bounds = SETTINGS_BY_ENV_VAR[env_var].bounds_for(level)
                    self.assertIsNone(bounds.minimum)
                    self.assertIsNone(bounds.maximum)

    def test_outside_original_scope_flags(self):
        self.assertEqual(11, len(OUTSIDE_ORIGINAL_SCOPE))
        for setting in SECURITY_SETTINGS:
            with self.subTest(env_var=setting.env_var):
                self.assertEqual(
                    setting.env_var not in OUTSIDE_ORIGINAL_SCOPE,
                    setting.original_scope,
                )

    def test_only_two_settings_can_be_disabled_with_zero(self):
        actual = {s.env_var for s in SECURITY_SETTINGS if s.zero_disables}
        self.assertEqual(DISABLING_ZERO_VARS, actual)
        self.assertEqual(
            "account lockout", SETTINGS_BY_ENV_VAR["LOGIN_MAX_ATTEMPTS"].zero_disables
        )
        self.assertEqual(
            "BI token expiry", SETTINGS_BY_ENV_VAR["BI_TOKEN_DURATION_DAYS"].zero_disables
        )

    def test_keys_and_infrastructure_are_not_in_the_inventory(self):
        names = set(SECRET_KEY_ENV_VARS) | {
            "FERNET_KEY",
            "SECRET_KEY",
            "SECRET_BI_KEY",
            "CORNFLOW_SECURITY_LEVEL",
            "CORNFLOW_SERVICE_API_KEY",
            "DATABASE_URL",
            "OPEN_DEPLOYMENT",
            "USER_ACCESS_ALL_OBJECTS",
            "DEFAULT_ROLE",
            "AUTH_TYPE",
            "LOG_LEVEL",
        }
        for name in names:
            with self.subTest(name=name):
                self.assertNotIn(name, SETTINGS_BY_ENV_VAR)

    def test_only_rate_limit_storage_is_sensitive(self):
        sensitive = {s.env_var for s in SECURITY_SETTINGS if s.sensitive}
        self.assertEqual({"RATELIMIT_STORAGE_URI"}, sensitive)

    def test_unset_variable_takes_the_level_default(self):
        for level in LEVELS:
            resolved = resolve(level)
            self.assertEqual((), resolved.changed)
            self.assertEqual((), resolved.adjusted)
            self.assertEqual((), resolved.errors)
            for env_var in EXPECTED_DEFAULTS:
                with self.subTest(level=level, env_var=env_var):
                    key = EXPECTED_CONFIG_KEYS[env_var]
                    self.assertEqual(expected_default(env_var, level), resolved.values[key])

    def test_valid_value_overrides_the_default(self):
        for level in LEVELS:
            for env_var in EXPECTED_DEFAULTS:
                with self.subTest(level=level, env_var=env_var):
                    raw = alternative_for(env_var, level)
                    expected = convert(env_var, raw)
                    default = expected_default(env_var, level)
                    self.assertNotEqual(default, expected)
                    resolved = resolve(level, **{env_var: raw})
                    key = EXPECTED_CONFIG_KEYS[env_var]
                    self.assertEqual(expected, resolved.values[key])
                    self.assertEqual((), resolved.adjusted)
                    self.assertEqual((), resolved.errors)
                    self.assertEqual(1, len(resolved.changed))
                    change = resolved.changed[0]
                    self.assertEqual(env_var, change.env_var)
                    self.assertEqual(key, change.config_key)
                    self.assertEqual(default, change.level_default)
                    self.assertEqual(expected, change.effective)

    def test_alternatives_cover_the_whole_inventory(self):
        # Guards the test data itself: every alternative must be inside the limits
        for level in LEVELS:
            for env_var in EXPECTED_DEFAULTS:
                with self.subTest(level=level, env_var=env_var):
                    raw = alternative_for(env_var, level)
                    self.assertNotEqual(expected_default(env_var, level), convert(env_var, raw))
                    if env_var in NUMERIC_VARS:
                        minimum, maximum = EXPECTED_BOUNDS.get(env_var, {}).get(
                            level, (None, None)
                        )
                        value = convert(env_var, raw)
                        if minimum is not None:
                            self.assertGreaterEqual(value, minimum)
                        if maximum is not None:
                            self.assertLessEqual(value, maximum)

    def test_out_of_bounds_value_is_clamped(self):
        for env_var, per_level in EXPECTED_BOUNDS.items():
            for level, (minimum, maximum) in per_level.items():
                key = EXPECTED_CONFIG_KEYS[env_var]
                default = expected_default(env_var, level)
                if maximum is not None:
                    with self.subTest(env_var=env_var, level=level, side="maximum"):
                        if env_var in FLOAT_VARS and env_var == "PWD_MAX_SIMILARITY":
                            raw = str(round(maximum + 0.05, 2))
                        else:
                            raw = str(maximum + 1)
                        resolved = resolve(level, **{env_var: raw})
                        self.assertEqual(maximum, resolved.values[key])
                        self.assertIs(
                            type(convert(env_var, "1")), type(resolved.values[key])
                        )
                        adjustment = by_env_var(resolved.adjusted)[env_var]
                        self.assertEqual(ADJUSTED_TO_MAXIMUM, adjustment.reason)
                        self.assertEqual(raw, adjustment.requested)
                        self.assertEqual(maximum, adjustment.applied)
                        self.assertEqual(level, adjustment.level)
                        self.assertEqual((), resolved.errors)
                        self.assertEqual(
                            maximum != default,
                            env_var in by_env_var(resolved.changed),
                        )
                if minimum is not None and not (
                    env_var in DISABLING_ZERO_VARS and minimum == 1
                ):
                    with self.subTest(env_var=env_var, level=level, side="minimum"):
                        raw = str(minimum - 1)
                        resolved = resolve(level, **{env_var: raw})
                        self.assertEqual(minimum, resolved.values[key])
                        self.assertIs(
                            type(convert(env_var, "1")), type(resolved.values[key])
                        )
                        adjustment = by_env_var(resolved.adjusted)[env_var]
                        self.assertEqual(ADJUSTED_TO_MINIMUM, adjustment.reason)
                        self.assertEqual(raw, adjustment.requested)
                        self.assertEqual(minimum, adjustment.applied)
                        self.assertEqual(level, adjustment.level)
                        self.assertEqual((), resolved.errors)
                        self.assertEqual(
                            minimum != default,
                            env_var in by_env_var(resolved.changed),
                        )

    def test_unbounded_side_keeps_extreme_values(self):
        for level in LEVELS:
            for env_var in NUMERIC_VARS:
                minimum, maximum = EXPECTED_BOUNDS.get(env_var, {}).get(
                    level, (None, None)
                )
                key = EXPECTED_CONFIG_KEYS[env_var]
                if maximum is None:
                    with self.subTest(env_var=env_var, level=level, side="maximum"):
                        resolved = resolve(level, **{env_var: "99999"})
                        self.assertEqual(99999, resolved.values[key])
                        self.assertEqual((), resolved.adjusted)
                        self.assertEqual((), resolved.errors)
                if minimum is None:
                    with self.subTest(env_var=env_var, level=level, side="minimum"):
                        resolved = resolve(level, **{env_var: "0"})
                        self.assertEqual(0, resolved.values[key])
                        self.assertEqual((), resolved.adjusted)
                        self.assertEqual((), resolved.errors)

    def test_negative_values_are_respected_without_a_minimum(self):
        self.assertEqual(-1, resolve(1, LOGIN_MAX_ATTEMPTS="-1").values["LOGIN_MAX_ATTEMPTS"])
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = resolve(level, ACCESS_TOKEN_DURATION_MINUTES="0")
                self.assertEqual(0, resolved.values["ACCESS_TOKEN_DURATION_MINUTES"])
                self.assertEqual((), resolved.adjusted)

    def test_disabling_zero_is_a_configuration_error(self):
        cases = (
            (2, "LOGIN_MAX_ATTEMPTS", "0", LOGIN_LOCKOUT_MESSAGE, 5),
            (2, "LOGIN_MAX_ATTEMPTS", "-1", LOGIN_LOCKOUT_MESSAGE, 5),
            (3, "LOGIN_MAX_ATTEMPTS", "0", LOGIN_LOCKOUT_MESSAGE, 5),
            (3, "LOGIN_MAX_ATTEMPTS", "-1", LOGIN_LOCKOUT_MESSAGE, 5),
            (3, "BI_TOKEN_DURATION_DAYS", "0", BI_EXPIRY_MESSAGE, 90),
            (3, "BI_TOKEN_DURATION_DAYS", "-3", BI_EXPIRY_MESSAGE, 90),
        )
        for level, env_var, raw, template, default in cases:
            with self.subTest(level=level, env_var=env_var, raw=raw):
                resolved = resolve(level, **{env_var: raw})
                self.assertEqual(
                    (template.format(value=int(raw), level=level),), resolved.errors
                )
                self.assertIsNone(resolved.level_error)
                self.assertEqual(resolved.errors, resolved.all_errors)
                self.assertEqual(default, resolved.values[env_var])
                self.assertNotIn(env_var, by_env_var(resolved.adjusted))
                self.assertNotIn(env_var, by_env_var(resolved.changed))

    def test_disabling_zero_is_allowed_where_the_level_admits_it(self):
        resolved = resolve(1, LOGIN_MAX_ATTEMPTS="0")
        self.assertEqual(0, resolved.values["LOGIN_MAX_ATTEMPTS"])
        self.assertEqual((), resolved.errors)
        self.assertEqual((), resolved.changed)
        for level in (1, 2):
            with self.subTest(level=level):
                resolved = resolve(level, BI_TOKEN_DURATION_DAYS="0")
                self.assertEqual(0, resolved.values["BI_TOKEN_DURATION_DAYS"])
                self.assertEqual((), resolved.errors)
                self.assertEqual((), resolved.adjusted)
                # 0 is the default of these levels, so it is not a change
                self.assertEqual((), resolved.changed)

    def test_two_disabling_zeros_register_two_errors(self):
        resolved = resolve(3, LOGIN_MAX_ATTEMPTS="0", BI_TOKEN_DURATION_DAYS="0")
        self.assertEqual(
            (
                LOGIN_LOCKOUT_MESSAGE.format(value=0, level=3),
                BI_EXPIRY_MESSAGE.format(value=0, level=3),
            ),
            resolved.errors,
        )
        self.assertEqual(resolved.errors, resolved.all_errors)
        self.assertEqual(5, resolved.values["LOGIN_MAX_ATTEMPTS"])
        self.assertEqual(90, resolved.values["BI_TOKEN_DURATION_DAYS"])

    def test_all_errors_puts_the_level_error_first(self):
        resolved = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: "x"})
        self.assertEqual((resolved.level_error,) + resolved.errors, resolved.all_errors)

    def test_unparseable_numeric_takes_the_default(self):
        cases = (
            ("LOGIN_MAX_ATTEMPTS", "abc"),
            ("PWD_MIN_LENGTH", "5.0"),
            ("PWD_MIN_LENGTH", "1.5"),
            ("MFA_REQUIRED", "true"),
            ("TOKEN_DURATION", "abc"),
            ("TOKEN_DURATION", "nan"),
            ("TOKEN_DURATION", "inf"),
            ("PWD_MAX_SIMILARITY", "NaN"),
        )
        for level in LEVELS:
            for env_var, raw in cases:
                with self.subTest(level=level, env_var=env_var, raw=raw):
                    resolved = resolve(level, **{env_var: raw})
                    key = EXPECTED_CONFIG_KEYS[env_var]
                    default = expected_default(env_var, level)
                    self.assertEqual(default, resolved.values[key])
                    self.assertEqual(1, len(resolved.adjusted))
                    adjustment = resolved.adjusted[0]
                    self.assertEqual(env_var, adjustment.env_var)
                    self.assertEqual(INVALID_VALUE, adjustment.reason)
                    self.assertEqual(raw, adjustment.requested)
                    self.assertEqual(default, adjustment.applied)
                    self.assertEqual(level, adjustment.level)
                    self.assertEqual((), resolved.changed)
                    self.assertEqual((), resolved.errors)

    def test_empty_numeric_counts_as_unset(self):
        for raw in ("", "   "):
            with self.subTest(raw=repr(raw)):
                resolved = resolve(2, TOKEN_DURATION=raw)
                self.assertEqual(8.0, resolved.values["TOKEN_DURATION"])
                self.assertEqual((), resolved.changed)
                self.assertEqual((), resolved.adjusted)
                self.assertEqual((), resolved.errors)

    def test_empty_disabling_variable_is_not_an_error(self):
        resolved = resolve(3, LOGIN_MAX_ATTEMPTS="", BI_TOKEN_DURATION_DAYS=" ")
        self.assertEqual((), resolved.errors)
        self.assertEqual(5, resolved.values["LOGIN_MAX_ATTEMPTS"])
        self.assertEqual(90, resolved.values["BI_TOKEN_DURATION_DAYS"])

    def test_string_values_are_taken_verbatim(self):
        resolved = resolve(1, CORS_ORIGINS="")
        self.assertEqual("", resolved.values["CORS_ORIGINS"])
        change = by_env_var(resolved.changed)["CORS_ORIGINS"]
        self.assertEqual("*", change.level_default)
        self.assertEqual("", change.effective)

        resolved = resolve(3, CORS_ORIGINS="https://ui.example.com")
        self.assertEqual("https://ui.example.com", resolved.values["CORS_ORIGINS"])
        self.assertIn("CORS_ORIGINS", by_env_var(resolved.changed))

        resolved = resolve(1, CONTENT_SECURITY_POLICY="")
        self.assertEqual("", resolved.values["CONTENT_SECURITY_POLICY"])
        self.assertIn("CONTENT_SECURITY_POLICY", by_env_var(resolved.changed))

        resolved = resolve(1, RATELIMIT_LOGIN=" 5 per minute ")
        self.assertEqual(" 5 per minute ", resolved.values["RATELIMIT_LOGIN"])

    def test_numeric_values_are_stripped(self):
        resolved = resolve(2, TOKEN_DURATION=" 12 ")
        self.assertEqual(12.0, resolved.values["TOKEN_DURATION"])
        self.assertEqual((), resolved.adjusted)

    def test_defined_value_equal_to_default_is_not_changed(self):
        resolved = resolve(2, TOKEN_DURATION="8", SIGNUP_ACTIVATED="3")
        self.assertEqual((), resolved.changed)
        self.assertEqual((), resolved.adjusted)
        resolved = resolve(3, CORS_ORIGINS="")
        self.assertEqual((), resolved.changed)

    def test_clamped_value_is_in_both_lists(self):
        resolved = resolve(2, TOKEN_DURATION="48")
        self.assertEqual(24.0, resolved.values["TOKEN_DURATION"])
        adjustment = resolved.adjusted[0]
        self.assertEqual(ADJUSTED_TO_MAXIMUM, adjustment.reason)
        self.assertEqual("48", adjustment.requested)
        self.assertEqual(24.0, adjustment.applied)
        change = resolved.changed[0]
        self.assertEqual(8.0, change.level_default)
        self.assertEqual(24.0, change.effective)

        resolved = resolve(3, BCRYPT_LOG_ROUNDS="4")
        self.assertEqual(12, resolved.values["BCRYPT_LOG_ROUNDS"])
        self.assertEqual(1, len(resolved.adjusted))
        self.assertEqual((), resolved.changed)

    def test_value_types(self):
        for level in LEVELS:
            for env_var in EXPECTED_DEFAULTS:
                raw = alternative_for(env_var, level)
                for resolved in (resolve(level), resolve(level, **{env_var: raw})):
                    with self.subTest(level=level, env_var=env_var):
                        value = resolved.values[EXPECTED_CONFIG_KEYS[env_var]]
                        if env_var in FLOAT_VARS:
                            self.assertIs(float, type(value))
                        elif env_var in STR_VARS:
                            self.assertIs(str, type(value))
                        elif env_var in OPTIONAL_STR_VARS:
                            self.assertIn(type(value), (str, type(None)))
                        else:
                            self.assertIs(int, type(value))
        self.assertIs(float, type(resolve(2, TOKEN_DURATION="12").values["TOKEN_DURATION"]))

    def test_resolution_is_pure(self):
        environ = {SECURITY_LEVEL_ENV_VAR: "2", "TOKEN_DURATION": "48"}
        snapshot = dict(environ)
        with patch.dict(
            os.environ, {SECURITY_LEVEL_ENV_VAR: "3", "TOKEN_DURATION": "1"}
        ):
            resolved = resolve_security_settings({})
            self.assertEqual(1, resolved.level)
            self.assertEqual(24.0, resolved.values["TOKEN_DURATION"])
            resolve_security_settings(environ)
        self.assertEqual(snapshot, environ)
        with self.assertRaises(TypeError):
            resolved.values["TOKEN_DURATION"] = 1

    def test_log_texts(self):
        resolved = resolve(2, TOKEN_DURATION="12")
        self.assertEqual(
            "TOKEN_DURATION: level default 8.0, effective 12.0",
            resolved.changed[0].as_log_text(),
        )

        resolved = resolve(2, TOKEN_DURATION="30")
        self.assertEqual(
            "TOKEN_DURATION: requested '30', applied 24.0 "
            "(maximum allowed at security level 2)",
            resolved.adjusted[0].as_log_text(),
        )

        resolved = resolve(1, BCRYPT_LOG_ROUNDS="10")
        self.assertEqual(
            "BCRYPT_LOG_ROUNDS: requested '10', applied 12 "
            "(minimum allowed at security level 1)",
            resolved.adjusted[0].as_log_text(),
        )

        resolved = resolve(2, LOGIN_MAX_ATTEMPTS="abc")
        self.assertEqual(
            "LOGIN_MAX_ATTEMPTS: requested 'abc' is not a valid int, "
            "applied the level default 5",
            resolved.adjusted[0].as_log_text(),
        )

        resolved = resolve(2, TOKEN_DURATION="abc")
        self.assertEqual(
            "TOKEN_DURATION: requested 'abc' is not a valid float, "
            "applied the level default 8.0",
            resolved.adjusted[0].as_log_text(),
        )

    def test_log_text_hides_sensitive_values(self):
        secret_uri = "redis://:s3cr3t@cache:6379/0"
        resolved = resolve(1, RATELIMIT_STORAGE_URI=secret_uri)
        change = resolved.changed[0]
        self.assertTrue(change.sensitive)
        text = change.as_log_text()
        self.assertEqual(
            "RATELIMIT_STORAGE_URI: level default memory://, "
            "effective value set (hidden)",
            text,
        )
        self.assertNotIn("s3cr3t", text)

    def test_log_text_writes_unset_for_none(self):
        resolved = resolve(1, CORNFLOW_UI_URL="https://ui.example.com")
        self.assertEqual(
            "CORNFLOW_UI_URL: level default unset, effective https://ui.example.com",
            resolved.changed[0].as_log_text(),
        )

    def test_result_objects_are_frozen(self):
        resolved = resolve(2, TOKEN_DURATION="48")
        for obj, attribute in (
            (resolved, "level"),
            (resolved.changed[0], "effective"),
            (resolved.adjusted[0], "applied"),
        ):
            with self.subTest(obj=type(obj).__name__):
                with self.assertRaises(Exception):
                    setattr(obj, attribute, 0)
        self.assertIsInstance(resolved.changed[0], SettingChange)
        self.assertIsInstance(resolved.adjusted[0], SettingAdjustment)

    def test_plan_examples(self):
        # Empty environment
        resolved = resolve(None)
        self.assertEqual(1, resolved.level)
        expected = {
            "MFA_ENABLED": 0,
            "MFA_REQUIRED": 0,
            "REFRESH_TOKEN_ENABLED": 0,
            "TOKEN_DURATION": 24,
            "LOGIN_MAX_ATTEMPTS": 0,
            "PWD_MIN_LENGTH": 5,
            "PWD_MIN_ZXCVBN_SCORE": 0,
            "PWD_ROTATION_ENFORCE": 0,
            "SIGNUP_ACTIVATED": 2,
            "BI_TOKEN_DURATION_DAYS": 0,
            "CORS_ORIGINS": "*",
            "DOCS_ENABLED": 1,
            "HSTS_ENABLED": 0,
        }
        for key, value in expected.items():
            with self.subTest(example="empty", key=key):
                self.assertEqual(value, resolved.values[key])

        # Level 2: as level 1 except five values
        level1 = resolve(1).values
        level2 = resolve(2).values
        differences = {k for k in level1 if level1[k] != level2[k]}
        self.assertEqual(
            {
                "TOKEN_DURATION",
                "PWD_MIN_LENGTH",
                "PWD_MIN_ZXCVBN_SCORE",
                "LOGIN_MAX_ATTEMPTS",
                "SIGNUP_ACTIVATED",
            },
            differences,
        )
        self.assertEqual(
            (8.0, 12, 3, 5, 3),
            tuple(
                level2[k]
                for k in (
                    "TOKEN_DURATION",
                    "PWD_MIN_LENGTH",
                    "PWD_MIN_ZXCVBN_SCORE",
                    "LOGIN_MAX_ATTEMPTS",
                    "SIGNUP_ACTIVATED",
                )
            ),
        )

        # Level 3: as level 2 except ten values
        level3 = resolve(3).values
        differences = {k for k in level2 if level2[k] != level3[k]}
        self.assertEqual(
            {
                "MFA_ENABLED",
                "MFA_REQUIRED",
                "API_KEY_STEPUP_TOTP",
                "PLATFORM_ROLE_STEPUP_TOTP",
                "REFRESH_TOKEN_ENABLED",
                "PWD_ROTATION_ENFORCE",
                "BI_TOKEN_DURATION_DAYS",
                "CORS_ORIGINS",
                "DOCS_ENABLED",
                "HSTS_ENABLED",
            },
            differences,
        )
        self.assertEqual("", level3["CORS_ORIGINS"])
        self.assertEqual(0, level3["DOCS_ENABLED"])
        self.assertEqual(1, level3["HSTS_ENABLED"])
        self.assertEqual(90, level3["BI_TOKEN_DURATION_DAYS"])

        # Level 1 has no limits except bcrypt
        resolved = resolve(1, TOKEN_DURATION="48")
        self.assertEqual(48.0, resolved.values["TOKEN_DURATION"])
        self.assertEqual((), resolved.adjusted)
        resolved = resolve(1, LOGIN_MAX_ATTEMPTS="0")
        self.assertEqual(0, resolved.values["LOGIN_MAX_ATTEMPTS"])
        self.assertEqual((), resolved.errors)
        resolved = resolve(1, PWD_MIN_LENGTH="3")
        self.assertEqual(3, resolved.values["PWD_MIN_LENGTH"])
        self.assertEqual((), resolved.adjusted)

        # Level 2 limits
        resolved = resolve(2, TOKEN_DURATION="48")
        self.assertEqual(24.0, resolved.values["TOKEN_DURATION"])
        self.assertEqual(1, len(resolved.adjusted))
        resolved = resolve(2, PWD_MIN_LENGTH="8")
        self.assertEqual(12, resolved.values["PWD_MIN_LENGTH"])
        self.assertEqual(1, len(resolved.adjusted))
        resolved = resolve(2, PWD_MIN_LENGTH="16")
        self.assertEqual(16, resolved.values["PWD_MIN_LENGTH"])
        self.assertEqual((), resolved.adjusted)
        resolved = resolve(2, LOGIN_MAX_ATTEMPTS="20")
        self.assertEqual(10, resolved.values["LOGIN_MAX_ATTEMPTS"])
        self.assertEqual(1, len(resolved.adjusted))

        # Level 3 and level 1 limits
        resolved = resolve(3, BI_TOKEN_DURATION_DAYS="500")
        self.assertEqual(365, resolved.values["BI_TOKEN_DURATION_DAYS"])
        self.assertEqual(1, len(resolved.adjusted))
        resolved = resolve(1, BCRYPT_LOG_ROUNDS="10")
        self.assertEqual(12, resolved.values["BCRYPT_LOG_ROUNDS"])
        self.assertEqual(1, len(resolved.adjusted))

        # A switch has no limits and is a change of the level
        resolved = resolve(2, SIGNUP_ACTIVATED="1")
        self.assertEqual(1, resolved.values["SIGNUP_ACTIVATED"])
        change = by_env_var(resolved.changed)["SIGNUP_ACTIVATED"]
        self.assertEqual((3, 1), (change.level_default, change.effective))

        # Invalid level: provisional level 1 values
        for raw in ("4", "abc", ""):
            resolved = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: raw})
            self.assertIsNotNone(resolved.level_error)
            self.assertEqual(expected_values(1), dict(resolved.values))


# ---------------------------------------------------------------------------
# apply_security_settings
# ---------------------------------------------------------------------------


class TestApplySecuritySettings(unittest.TestCase):
    def test_sets_every_key_and_the_metadata(self):
        resolved = resolve(2, TOKEN_DURATION="12", LOGIN_MAX_ATTEMPTS="abc")
        cls = type("Empty", (), {})
        returned = apply_security_settings(cls, resolved)
        self.assertIs(cls, returned)
        for key, value in resolved.values.items():
            with self.subTest(key=key):
                self.assertEqual(value, getattr(cls, key))
        self.assertEqual(47, len(resolved.values))
        self.assertEqual(
            {
                "SECURITY_LEVEL": 2,
                "SECURITY_LEVEL_ERROR": None,
                "SECURITY_CONFIG_ERRORS": (),
                "SECURITY_CHANGED_SETTINGS": resolved.changed,
                "SECURITY_ADJUSTED_SETTINGS": resolved.adjusted,
            },
            {key: getattr(cls, key) for key in METADATA_CONFIG_KEYS},
        )

    def test_metadata_with_errors(self):
        resolved = resolve_security_settings({SECURITY_LEVEL_ENV_VAR: "abc"})
        cls = apply_security_settings(type("Invalid", (), {}), resolved)
        self.assertEqual(1, cls.SECURITY_LEVEL)
        self.assertEqual(resolved.level_error, cls.SECURITY_LEVEL_ERROR)

        resolved = resolve(2, LOGIN_MAX_ATTEMPTS="0")
        cls = apply_security_settings(type("Zero", (), {}), resolved)
        self.assertEqual(resolved.errors, cls.SECURITY_CONFIG_ERRORS)
        self.assertEqual(1, len(cls.SECURITY_CONFIG_ERRORS))

    def test_class_body_wins(self):
        class WithBody:
            CORS_ORIGINS = "x"

        apply_security_settings(WithBody, resolve(3))
        self.assertEqual("x", WithBody.CORS_ORIGINS)
        self.assertEqual(8.0, WithBody.TOKEN_DURATION)
        self.assertEqual(3, WithBody.SECURITY_LEVEL)

    def test_inherited_values_are_replaced(self):
        parent = apply_security_settings(type("Parent", (), {}), resolve(3))
        child = apply_security_settings(type("Child", (parent,), {}), resolve(1))
        self.assertEqual(24.0, child.TOKEN_DURATION)
        self.assertEqual(1, child.SECURITY_LEVEL)
        self.assertEqual("*", child.CORS_ORIGINS)
        self.assertEqual(8.0, parent.TOKEN_DURATION)
        self.assertEqual(3, parent.SECURITY_LEVEL)


# ---------------------------------------------------------------------------
# Configuration classes
# ---------------------------------------------------------------------------


class TestConfigClasses(unittest.TestCase):
    TESTING_DEVIATIONS = {
        "CORS_ORIGINS": "*",
        "DOCS_ENABLED": 1,
        "HSTS_ENABLED": 0,
        "MFA_REQUIRED": 0,
        "RATELIMIT_ENABLED": 0,
        "BCRYPT_LOG_ROUNDS": 4,
        "SIGNUP_ACTIVATED": 1,
    }

    def test_testing_is_level_3_with_its_own_deviations(self):
        self.assertEqual(3, Testing.SECURITY_LEVEL)
        self.assertIsNone(Testing.SECURITY_LEVEL_ERROR)
        self.assertEqual((), Testing.SECURITY_CONFIG_ERRORS)
        self.assertEqual((), Testing.SECURITY_CHANGED_SETTINGS)
        self.assertEqual((), Testing.SECURITY_ADJUSTED_SETTINGS)
        expected = {**expected_values(3), **self.TESTING_DEVIATIONS}
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(value, getattr(Testing, key))
        self.assertEqual(1, Testing.MFA_ENABLED)
        self.assertEqual("testing", Testing.ENV)
        self.assertTrue(Testing.TESTING)
        self.assertEqual(1, Testing.OPEN_DEPLOYMENT)
        self.assertEqual(
            "TESTINGSECRETKEY_TESTINGSECRETKEY_32B", Testing.SECRET_TOKEN_KEY
        )
        self.assertEqual("THISISANOTHERKEY_THISISANOTHERKEY_32B", Testing.SECRET_BI_KEY)

    def test_testing_subclasses_keep_working(self):
        self.assertEqual(1, TestingRateLimit.RATELIMIT_ENABLED)
        self.assertEqual("3 per minute", TestingRateLimit.RATELIMIT_LOGIN)
        for cls in (TestingOpenAuth, TestingApplicationRoot, TestingDatabricks):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(3, cls.SECURITY_LEVEL)
                self.assertEqual(0, cls.RATELIMIT_ENABLED)

    def test_every_config_class_exposes_the_inventory(self):
        config_keys = set(EXPECTED_CONFIG_KEYS.values())
        for name, cls in app_config.items():
            for key in config_keys | set(METADATA_CONFIG_KEYS):
                with self.subTest(config=name, key=key):
                    self.assertTrue(hasattr(cls, key))

    def test_development_and_production_do_not_override_the_inventory(self):
        keys = set(EXPECTED_CONFIG_KEYS.values()) | set(METADATA_CONFIG_KEYS)
        for cls in (Development, Production):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(set(), keys & set(cls.__dict__))
        self.assertIs(False, Production.DEBUG)
        self.assertIs(False, Production.TESTING)
        self.assertIs(True, Production.PROPAGATE_EXCEPTIONS)

    def test_development_and_production_have_the_same_values(self):
        for key in EXPECTED_CONFIG_KEYS.values():
            with self.subTest(key=key):
                self.assertEqual(getattr(Development, key), getattr(Production, key))

    def test_config_helpers_are_gone(self):
        import cornflow.config as config

        for name in ("_env_int_floor", "_env_int_ceiling", "_env_float_ceiling"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(config, name))


# ---------------------------------------------------------------------------
# Reading the real environment (subprocess)
# ---------------------------------------------------------------------------

_IMPORT_SCRIPT = """
import json
from cornflow.config import DefaultConfig, Development, Production, Testing
from cornflow.shared.security_levels import SECURITY_SETTINGS

keys = [setting.config_key for setting in SECURITY_SETTINGS]
out = {}
for cls in (DefaultConfig, Development, Production, Testing):
    data = {key: getattr(cls, key) for key in keys}
    data["SECURITY_LEVEL"] = cls.SECURITY_LEVEL
    data["SECURITY_LEVEL_ERROR"] = cls.SECURITY_LEVEL_ERROR
    data["SECURITY_CONFIG_ERRORS"] = list(cls.SECURITY_CONFIG_ERRORS)
    data["CHANGED"] = len(cls.SECURITY_CHANGED_SETTINGS)
    data["ADJUSTED"] = len(cls.SECURITY_ADJUSTED_SETTINGS)
    out[cls.__name__] = data
print(json.dumps(out))
"""


def _import_config(env_overrides):
    """
    Imports cornflow.config in a new interpreter whose environment has none of
    the security variables except the given ones, and returns the values of
    the configuration classes.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if name != SECURITY_LEVEL_ENV_VAR and name not in EXPECTED_DEFAULTS
    }
    env.update(env_overrides)
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"importing cornflow.config failed with code {result.returncode}: "
            f"{result.stderr[-2000:]}"
        )
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestConfigImportReadsTheEnvironment(unittest.TestCase):
    def test_no_variables_is_level_1(self):
        data = _import_config({})["DefaultConfig"]
        self.assertEqual(1, data["SECURITY_LEVEL"])
        self.assertIsNone(data["SECURITY_LEVEL_ERROR"])
        self.assertEqual([], data["SECURITY_CONFIG_ERRORS"])
        expected = {
            "MFA_ENABLED": 0,
            "MFA_REQUIRED": 0,
            "REFRESH_TOKEN_ENABLED": 0,
            "TOKEN_DURATION": 24.0,
            "LOGIN_MAX_ATTEMPTS": 0,
            "PWD_MIN_LENGTH": 5,
            "PWD_MIN_ZXCVBN_SCORE": 0,
            "PWD_ROTATION_ENFORCE": 0,
            "SIGNUP_ACTIVATED": 2,
            "BI_TOKEN_DURATION_DAYS": 0,
            "CORS_ORIGINS": "*",
            "DOCS_ENABLED": 1,
            "HSTS_ENABLED": 0,
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(value, data[key])
        self.assertEqual(expected_values(1), {k: data[k] for k in expected_values(1)})

    def test_level_3_is_strict_with_any_flask_env(self):
        result = _import_config(
            {SECURITY_LEVEL_ENV_VAR: "3", "FLASK_ENV": "development"}
        )
        for name in ("Development", "Production"):
            with self.subTest(cls=name):
                self.assertEqual(3, result[name]["SECURITY_LEVEL"])
                self.assertEqual("", result[name]["CORS_ORIGINS"])
                self.assertEqual(0, result[name]["DOCS_ENABLED"])
                self.assertEqual(1, result[name]["HSTS_ENABLED"])

    def test_level_1_is_open_in_production(self):
        result = _import_config({SECURITY_LEVEL_ENV_VAR: "1", "FLASK_ENV": "production"})
        production = result["Production"]
        self.assertEqual("*", production["CORS_ORIGINS"])
        self.assertEqual(1, production["DOCS_ENABLED"])
        self.assertEqual(0, production["HSTS_ENABLED"])

    def test_development_equals_production(self):
        result = _import_config(
            {
                SECURITY_LEVEL_ENV_VAR: "2",
                "TOKEN_DURATION": "12",
                "CORS_ORIGINS": "https://ui.example.com",
            }
        )
        self.assertEqual(result["Development"], result["Production"])
        self.assertEqual(12.0, result["Production"]["TOKEN_DURATION"])
        self.assertEqual("https://ui.example.com", result["Production"]["CORS_ORIGINS"])
        self.assertEqual(2, result["Production"]["SECURITY_LEVEL"])

    def test_invalid_level_does_not_break_the_import(self):
        result = _import_config({SECURITY_LEVEL_ENV_VAR: "abc"})
        data = result["DefaultConfig"]
        self.assertTrue(data["SECURITY_LEVEL_ERROR"])
        self.assertIn("CORNFLOW_SECURITY_LEVEL", data["SECURITY_LEVEL_ERROR"])
        self.assertEqual(1, data["SECURITY_LEVEL"])

    def test_disabling_zero_does_not_break_the_import(self):
        result = _import_config({SECURITY_LEVEL_ENV_VAR: "2", "LOGIN_MAX_ATTEMPTS": "0"})
        data = result["DefaultConfig"]
        self.assertEqual(1, len(data["SECURITY_CONFIG_ERRORS"]))
        self.assertEqual(
            LOGIN_LOCKOUT_MESSAGE.format(value=0, level=2),
            data["SECURITY_CONFIG_ERRORS"][0],
        )
        self.assertEqual(5, data["LOGIN_MAX_ATTEMPTS"])

    def test_changes_and_adjustments_are_recorded(self):
        result = _import_config(
            {SECURITY_LEVEL_ENV_VAR: "2", "TOKEN_DURATION": "48", "SIGNUP_ACTIVATED": "1"}
        )
        data = result["DefaultConfig"]
        self.assertEqual(24.0, data["TOKEN_DURATION"])
        self.assertEqual(2, data["CHANGED"])
        self.assertEqual(1, data["ADJUSTED"])

    def test_testing_ignores_the_environment(self):
        result = _import_config(
            {
                SECURITY_LEVEL_ENV_VAR: "1",
                "TOKEN_DURATION": "48",
                "MFA_REQUIRED": "1",
            }
        )
        testing = result["Testing"]
        self.assertEqual(3, testing["SECURITY_LEVEL"])
        self.assertEqual(8.0, testing["TOKEN_DURATION"])
        self.assertEqual(0, testing["MFA_REQUIRED"])
        self.assertEqual(0, testing["CHANGED"])
        self.assertEqual(0, testing["ADJUSTED"])
        # The environment did apply to the classes that read it
        self.assertEqual(48.0, result["DefaultConfig"]["TOKEN_DURATION"])
        self.assertEqual(1, result["DefaultConfig"]["MFA_REQUIRED"])


# ---------------------------------------------------------------------------
# Per-level test helper
# ---------------------------------------------------------------------------


class TestSecurityLevelHelper(unittest.TestCase):
    FIXTURES = {"BCRYPT_LOG_ROUNDS": 4, "RATELIMIT_ENABLED": 0}

    def test_returns_a_registered_testing_subclass(self):
        name = security_level_config(2)
        self.assertIn(name, app_config)
        self.assertTrue(issubclass(app_config[name], Testing))
        self.assertEqual(name, security_level_config(2))
        self.assertIs(app_config[name], app_config[security_level_config(2)])
        self.assertNotEqual(name, security_level_config(3))
        self.assertNotEqual(name, security_level_config(2, TOKEN_DURATION=12))

    def test_level_values(self):
        for level in LEVELS:
            cls = build_security_level_config(level)
            expected = {**expected_values(level), **self.FIXTURES}
            self.assertEqual(level, cls.SECURITY_LEVEL)
            for key, value in expected.items():
                with self.subTest(level=level, key=key):
                    self.assertEqual(value, getattr(cls, key))

    def test_level_values_through_the_registered_name(self):
        cls = app_config[security_level_config(1)]
        self.assertEqual(1, cls.SECURITY_LEVEL)
        self.assertEqual(24.0, cls.TOKEN_DURATION)
        self.assertEqual(4, cls.BCRYPT_LOG_ROUNDS)

    def test_level_none_leaves_the_selector_unset(self):
        cls = build_security_level_config(None)
        self.assertEqual(1, cls.SECURITY_LEVEL)
        self.assertIsNone(cls.SECURITY_LEVEL_ERROR)

    def test_overrides_go_through_the_resolution(self):
        cls = build_security_level_config(2, TOKEN_DURATION=48)
        self.assertEqual(24.0, cls.TOKEN_DURATION)
        self.assertEqual(1, len(cls.SECURITY_ADJUSTED_SETTINGS))
        self.assertEqual("TOKEN_DURATION", cls.SECURITY_ADJUSTED_SETTINGS[0].env_var)

        cls = build_security_level_config(2, DOCS_ENABLED=0)
        self.assertEqual(0, cls.DOCS_ENABLED)
        changed = cls.SECURITY_CHANGED_SETTINGS
        self.assertEqual(["DOCS_ENABLED"], [change.config_key for change in changed])

        cls = build_security_level_config(1, MFA_REQUIRED=True)
        self.assertEqual(1, cls.MFA_REQUIRED)

        cls = build_security_level_config(1, CORNFLOW_UI_URL=None)
        self.assertIsNone(cls.CORNFLOW_UI_URL)

    def test_disabling_zero_and_invalid_level_are_recorded(self):
        cls = app_config[security_level_config(2, LOGIN_MAX_ATTEMPTS=0)]
        self.assertEqual(1, len(cls.SECURITY_CONFIG_ERRORS))
        self.assertEqual(5, cls.LOGIN_MAX_ATTEMPTS)
        cls = app_config[security_level_config("abc")]
        self.assertIsNotNone(cls.SECURITY_LEVEL_ERROR)
        self.assertEqual(1, cls.SECURITY_LEVEL)

    def test_raw_environ(self):
        cls = build_security_level_config(2, environ={"LOGIN_MAX_ATTEMPTS": "abc"})
        self.assertEqual(5, cls.LOGIN_MAX_ATTEMPTS)
        self.assertEqual(
            [INVALID_VALUE], [a.reason for a in cls.SECURITY_ADJUSTED_SETTINGS]
        )
        cls = build_security_level_config(1, environ={"CORS_ORIGINS": ""})
        self.assertEqual("", cls.CORS_ORIGINS)
        with self.assertRaises(ValueError):
            build_security_level_config(
                2, environ={"TOKEN_DURATION": "12"}, TOKEN_DURATION=10
            )

    def test_non_inventory_overrides_are_set_as_is(self):
        cls = build_security_level_config(2, OPEN_DEPLOYMENT=0, SECRET_TOKEN_KEY="x" * 40)
        self.assertEqual(0, cls.OPEN_DEPLOYMENT)
        self.assertEqual("x" * 40, cls.SECRET_TOKEN_KEY)

    def test_metadata_overrides_are_rejected(self):
        for key in METADATA_CONFIG_KEYS:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_security_level_config(2, **{key: 2})

    def test_rate_limit_can_be_enabled(self):
        self.assertEqual(0, build_security_level_config(1).RATELIMIT_ENABLED)
        self.assertEqual(1, build_security_level_config(1, RATELIMIT_ENABLED=1).RATELIMIT_ENABLED)
        self.assertEqual(
            1, build_security_level_config(1, environ={"RATELIMIT_ENABLED": "1"}).RATELIMIT_ENABLED
        )

    def test_create_app_works_at_every_level(self):
        for level in LEVELS:
            with self.subTest(level=level):
                app = create_app(security_level_config(level))
                self.assertEqual(level, app.config["SECURITY_LEVEL"])


# ---------------------------------------------------------------------------
# Login smoke test per level
# ---------------------------------------------------------------------------


class LoginSmokeBase(SecurityLevelTestMixin, TestCase):
    security_level = 1

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        user = UserModel(
            {
                "username": "smokeuser",
                "email": "smokeuser@test.com",
                "password": PASSWORD,
            }
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": PLANNER_ROLE}).save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self):
        response = self.client.post(
            LOGIN_URL,
            json={"username": "smokeuser", "password": PASSWORD},
        )
        self.assertEqual(200, response.status_code, response.json)
        return response.json

    def session_lifetime(self, token):
        claims = jwt.decode(token, options={"verify_signature": False})
        return claims["exp"] - claims["iat"]


class _SingleSessionSmoke:
    expected_hours = None

    def test_login_returns_only_a_session_token(self):
        body = self.login()
        self.assertIn("token", body)
        self.assertNotIn("refresh_token", body)
        self.assertAlmostEqual(
            self.expected_hours * 3600, self.session_lifetime(body["token"]), delta=5
        )


class TestLoginSmokeLevel1(_SingleSessionSmoke, LoginSmokeBase):
    security_level = 1
    expected_hours = 24


class TestLoginSmokeLevel2(_SingleSessionSmoke, LoginSmokeBase):
    security_level = 2
    expected_hours = 8


class TestLoginSmokeLevel3(LoginSmokeBase):
    security_level = 3
    # The smoke test looks at the session format, not at the MFA enrolment
    config_overrides = {"MFA_REQUIRED": 0}

    def test_login_returns_a_session_with_refresh_token(self):
        body = self.login()
        self.assertIn("token", body)
        self.assertIn("refresh_token", body)


if __name__ == "__main__":
    unittest.main()
