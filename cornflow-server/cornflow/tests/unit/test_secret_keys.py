"""
Tests of the secret keys (FERNET_KEY > SECRET_KEY > random at level 1) and of
their validation per security level:

- the pure resolution and the pure check of cornflow.shared.secret_keys,
- the startup checks of create_app,
- the reading of the real environment by cornflow.config (subprocess),
- tokens and encrypted secrets across applications that share the database,
- ``cornflow service init`` and the keys it passes to the gunicorn workers,
- the CLI signing with the key of the server,
- the warning when an API key is signed with the random key.

The expected messages come from the functions and constants of
cornflow.shared.secret_keys (the texts are checked there against the
specification); the rest of the expectations are written in this file.

cornflow.shared.secret_keys is imported lazily (through ``sk``) so that a
missing module only makes the tests that use it fail.
"""

import base64
import contextlib
import copy
import importlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from click.testing import CliRunner
from cryptography.fernet import Fernet
from flask import Flask
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.commands.access import access_init_command
from cornflow.config import app_config
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.authentication import Auth
from cornflow.shared.authentication.auth import BIAuth
from cornflow.shared.const import PLANNER_ROLE
from cornflow.shared.encryption import decrypt_value, encrypt_value
from cornflow.shared.exceptions import (
    ConfigurationError,
    InvalidCredentials,
    InvalidUsage,
)
from cornflow.tests.const import INSTANCE_URL, LOGIN_URL, PREFIX
from cornflow.tests.security_levels_support import (
    build_security_level_config,
    security_level_config,
)


class _LazyModule:
    def __getattr__(self, name):
        module = importlib.import_module("cornflow.shared.secret_keys")
        return getattr(module, name)


sk = _LazyModule()

LEVELS = (1, 2, 3)
APP_LOGGER = "cornflow.app"
SERVICE_LOGGER = "cornflow.service"
PASSWORD = "Kx9#tR2m!Qw7Zp"
API_KEY_URL = PREFIX + "/user/api-key/"

KEY_A = Fernet.generate_key().decode()
KEY_B = Fernet.generate_key().decode()
BI_KEY = Fernet.generate_key().decode()
SHORT = "weak-key-0123456789!"
L31 = "a" * 31
L32 = "b" * 32
BI_23 = "c" * 23
BI_32 = "d" * 32
TESTING_TOKEN_KEY = "TESTINGSECRETKEY_TESTINGSECRETKEY_32B"
KEY_VARS = (
    "FERNET_KEY",
    "SECRET_KEY",
    "SECRET_BI_KEY",
    "CORNFLOW_EPHEMERAL_SECRET_KEY",
)
# Words that identify the messages about the secret keys
KEY_MESSAGE_MARKERS = ("secret key", "FERNET_KEY", "SECRET_TOKEN_KEY", "SECRET_BI_KEY")
# The command that the key messages suggest, and the code that it runs
FERNET_KEY_CODE = (
    "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
)
FERNET_KEY_COMMAND = f'python -c "{FERNET_KEY_CODE}"'

assert KEY_A != KEY_B and len(KEY_A) == len(BI_KEY) == 44
assert (len(SHORT), len(L31), len(L32), len(BI_23)) == (20, 31, 32, 23)


def level_overrides(level, **extra):
    """Level 3 requires MFA by default: the key tests do not enrol users."""
    overrides = {"MFA_REQUIRED": 0} if level == 3 else {}
    overrides.update(extra)
    return overrides


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def lines(self, level=None):
        return [
            record.getMessage()
            for record in self.records
            if level is None or record.levelno == level
        ]


@contextlib.contextmanager
def capture_log(name=APP_LOGGER, level=None):
    """
    Captures the records of a logger. dictConfig is replaced by a no-op while
    the application is created, otherwise create_app would reset the handlers
    of the logger and drop the capture.
    """
    handler = _ListHandler()
    logger = logging.getLogger(name)
    previous_level = logger.level
    logger.addHandler(handler)
    if level is not None:
        logger.setLevel(level)
    try:
        with mock.patch("cornflow.app.dictConfig"):
            yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def key_lines(handler):
    """The WARNING records about the secret keys."""
    return [
        line
        for line in handler.lines(logging.WARNING)
        if any(marker in line for marker in KEY_MESSAGE_MARKERS)
    ]


def start(level, key_environ, **overrides):
    """create_app with the keys of key_environ, capturing the log."""
    name = security_level_config(
        level,
        key_environ=key_environ,
        **level_overrides(level, LOG_LEVEL=logging.INFO, **overrides),
    )
    with capture_log() as handler:
        app = create_app(name)
    return app, handler


def start_fails(case, level, key_environ, **overrides):
    """create_app that must refuse to start; returns (exception, handler)."""
    name = security_level_config(
        level,
        key_environ=key_environ,
        **level_overrides(level, LOG_LEVEL=logging.INFO, **overrides),
    )
    with capture_log() as handler:
        with case.assertRaises(ConfigurationError) as ctx:
            create_app(name)
    return ctx.exception, handler


class KeyTestCase(unittest.TestCase):
    def assertNoKeyValue(self, text, *extra):
        for secret in (KEY_A, KEY_B, BI_KEY, SHORT, *extra):
            self.assertNotIn(secret, text)


# ---------------------------------------------------------------------------
# Pure resolution
# ---------------------------------------------------------------------------


class TestResolveSecretKeys(KeyTestCase):
    @staticmethod
    def resolve(environ, level=1, generate=None):
        if generate is None:
            return sk.resolve_secret_keys(environ, level)
        return sk.resolve_secret_keys(environ, level, generate)

    def test_constants(self):
        self.assertEqual("FERNET_KEY", sk.FERNET_KEY_ENV_VAR)
        self.assertEqual("SECRET_KEY", sk.SECRET_KEY_ENV_VAR)
        self.assertEqual("SECRET_BI_KEY", sk.SECRET_BI_KEY_ENV_VAR)
        self.assertEqual(
            "CORNFLOW_EPHEMERAL_SECRET_KEY", sk.EPHEMERAL_SECRET_KEY_ENV_VAR
        )
        self.assertEqual(32, sk.MINIMUM_SECRET_KEY_LENGTH)
        self.assertEqual("SECRET_KEY_SOURCE", sk.CONFIG_KEY_SECRET_KEY_SOURCE)
        self.assertEqual("SECRET_KEYS_DIFFER", sk.CONFIG_KEY_SECRET_KEYS_DIFFER)
        self.assertEqual(
            ["FERNET_KEY", "SECRET_KEY", "random", "missing", "config"],
            [
                sk.KEY_SOURCE_FERNET_KEY,
                sk.KEY_SOURCE_SECRET_KEY,
                sk.KEY_SOURCE_RANDOM,
                sk.KEY_SOURCE_MISSING,
                sk.KEY_SOURCE_CONFIG,
            ],
        )

    def test_fernet_key_wins(self):
        for level in LEVELS:
            with self.subTest(level=level, case="only FERNET_KEY"):
                resolved = self.resolve({"FERNET_KEY": KEY_A}, level)
                self.assertEqual(KEY_A, resolved.token_key)
                self.assertEqual("FERNET_KEY", resolved.source)
                self.assertFalse(resolved.keys_differ)
            with self.subTest(level=level, case="both, different"):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_B}, level
                )
                self.assertEqual(KEY_A, resolved.token_key)
                self.assertEqual("FERNET_KEY", resolved.source)
                self.assertTrue(resolved.keys_differ)
            with self.subTest(level=level, case="both, equal"):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_A}, level
                )
                self.assertEqual(KEY_A, resolved.token_key)
                self.assertFalse(resolved.keys_differ)

    def test_secret_key_is_the_fallback(self):
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = self.resolve({"SECRET_KEY": KEY_B}, level)
                self.assertEqual(KEY_B, resolved.token_key)
                self.assertEqual("SECRET_KEY", resolved.source)
                self.assertFalse(resolved.keys_differ)

    def test_bi_key_is_read_as_is_and_never_random(self):
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}, level
                )
                self.assertEqual(BI_KEY, resolved.bi_key)
                self.assertIsNone(self.resolve({"FERNET_KEY": KEY_A}, level).bi_key)
                self.assertIsNone(self.resolve({}, level).bi_key)

    def test_empty_counts_as_unset(self):
        for level in LEVELS:
            for empty in ("", "   "):
                with self.subTest(level=level, empty=repr(empty)):
                    resolved = self.resolve(
                        {"FERNET_KEY": empty, "SECRET_KEY": KEY_B}, level
                    )
                    self.assertEqual(KEY_B, resolved.token_key)
                    self.assertEqual("SECRET_KEY", resolved.source)
                    self.assertFalse(resolved.keys_differ)
            with self.subTest(level=level, case="empty SECRET_KEY"):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_KEY": ""}, level
                )
                self.assertEqual(KEY_A, resolved.token_key)
                self.assertFalse(resolved.keys_differ)
            with self.subTest(level=level, case="empty SECRET_BI_KEY"):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": ""}, level
                )
                self.assertIsNone(resolved.bi_key)
        resolved = self.resolve({"FERNET_KEY": ""}, 1)
        self.assertEqual("random", resolved.source)
        for level in (2, 3):
            with self.subTest(level=level, case="only an empty FERNET_KEY"):
                resolved = self.resolve({"FERNET_KEY": ""}, level)
                self.assertEqual("missing", resolved.source)
                self.assertIsNone(resolved.token_key)

    def test_values_are_not_stripped(self):
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = self.resolve({"FERNET_KEY": " " + KEY_A}, level)
                self.assertEqual(" " + KEY_A, resolved.token_key)
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY + " "}, level
                )
                self.assertEqual(BI_KEY + " ", resolved.bi_key)

    def test_no_key_at_level_1_is_random(self):
        generate = mock.Mock(return_value="R" * 64)
        resolved = self.resolve({}, 1, generate)
        self.assertEqual("R" * 64, resolved.token_key)
        self.assertEqual("random", resolved.source)
        self.assertFalse(resolved.keys_differ)
        generate.assert_called_once_with()

        first = self.resolve({}, 1)
        second = self.resolve({}, 1)
        self.assertRegex(first.token_key, r"^[0-9a-f]{64}$")
        self.assertNotEqual(first.token_key, second.token_key)
        self.assertRegex(sk.generate_secret_key(), r"^[0-9a-f]{64}$")

    def test_a_defined_key_does_not_generate(self):
        for environ in ({"FERNET_KEY": KEY_A}, {"SECRET_KEY": KEY_B}):
            with self.subTest(environ=sorted(environ)):
                generate = mock.Mock(return_value="R" * 64)
                self.resolve(environ, 1, generate)
                generate.assert_not_called()

    def test_no_key_at_levels_2_and_3_is_missing(self):
        for level in (2, 3):
            with self.subTest(level=level):
                generate = mock.Mock(return_value="R" * 64)
                resolved = self.resolve({"SECRET_BI_KEY": BI_KEY}, level, generate)
                self.assertIsNone(resolved.token_key)
                self.assertEqual("missing", resolved.source)
                self.assertEqual(BI_KEY, resolved.bi_key)
                generate.assert_not_called()

    def test_ephemeral_key(self):
        ephemeral = "E" * 64
        generate = mock.Mock(return_value="R" * 64)
        resolved = self.resolve(
            {"CORNFLOW_EPHEMERAL_SECRET_KEY": ephemeral}, 1, generate
        )
        self.assertEqual(ephemeral, resolved.token_key)
        self.assertEqual("random", resolved.source)
        generate.assert_not_called()

        resolved = self.resolve(
            {"CORNFLOW_EPHEMERAL_SECRET_KEY": ephemeral, "FERNET_KEY": KEY_A}, 1
        )
        self.assertEqual(KEY_A, resolved.token_key)
        self.assertEqual("FERNET_KEY", resolved.source)

        for level in (2, 3):
            with self.subTest(level=level):
                resolved = self.resolve(
                    {"CORNFLOW_EPHEMERAL_SECRET_KEY": ephemeral}, level, generate
                )
                self.assertIsNone(resolved.token_key)
                self.assertEqual("missing", resolved.source)
        generate.assert_not_called()

    def test_environ_is_not_mutated(self):
        environ = {
            "FERNET_KEY": KEY_A,
            "SECRET_KEY": KEY_B,
            "SECRET_BI_KEY": BI_KEY,
            "CORNFLOW_EPHEMERAL_SECRET_KEY": "E" * 64,
        }
        for level in LEVELS:
            for variables in (environ, {}, {"FERNET_KEY": ""}):
                with self.subTest(level=level, variables=sorted(variables)):
                    before = copy.deepcopy(variables)
                    self.resolve(variables, level)
                    self.assertEqual(before, variables)

    def test_the_process_environment_is_not_read(self):
        with mock.patch.dict(
            os.environ, {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}
        ):
            resolved = self.resolve({}, 2)
        self.assertEqual("missing", resolved.source)
        self.assertIsNone(resolved.bi_key)

    def test_repr_hides_keys(self):
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = self.resolve(
                    {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}, level
                )
                self.assertNoKeyValue(repr(resolved))
        random_key = self.resolve({}, 1)
        self.assertNoKeyValue(repr(random_key), random_key.token_key)

    def test_resolved_keys_are_immutable(self):
        resolved = self.resolve({"FERNET_KEY": KEY_A}, 1)
        with self.assertRaises(Exception):
            resolved.token_key = "other"


class TestApplySecretKeys(KeyTestCase):
    def test_sets_the_four_values(self):
        class Config:
            pass

        resolved = sk.resolve_secret_keys(
            {"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_B, "SECRET_BI_KEY": BI_KEY}, 2
        )
        result = sk.apply_secret_keys(Config, resolved)
        self.assertIs(Config, result)
        self.assertEqual(KEY_A, Config.SECRET_TOKEN_KEY)
        self.assertEqual(BI_KEY, Config.SECRET_BI_KEY)
        self.assertEqual("FERNET_KEY", Config.SECRET_KEY_SOURCE)
        self.assertTrue(Config.SECRET_KEYS_DIFFER)

    def test_class_body_wins(self):
        class Config:
            SECRET_TOKEN_KEY = "fixed-token-key"
            SECRET_KEY_SOURCE = "config"

        resolved = sk.resolve_secret_keys({"FERNET_KEY": KEY_A}, 1)
        sk.apply_secret_keys(Config, resolved)
        self.assertEqual("fixed-token-key", Config.SECRET_TOKEN_KEY)
        self.assertEqual("config", Config.SECRET_KEY_SOURCE)
        self.assertFalse(Config.SECRET_KEYS_DIFFER)
        self.assertIsNone(Config.SECRET_BI_KEY)

    def test_inherited_values_are_replaced(self):
        class Parent:
            SECRET_TOKEN_KEY = "parent-key"
            SECRET_KEY_SOURCE = "config"

        class Child(Parent):
            pass

        sk.apply_secret_keys(Child, sk.resolve_secret_keys({"SECRET_KEY": KEY_B}, 1))
        self.assertEqual(KEY_B, Child.SECRET_TOKEN_KEY)
        self.assertEqual("SECRET_KEY", Child.SECRET_KEY_SOURCE)
        self.assertEqual("parent-key", Parent.SECRET_TOKEN_KEY)

    def test_uses_random_secret_key_and_key_length(self):
        self.assertTrue(sk.uses_random_secret_key({"SECRET_KEY_SOURCE": "random"}))
        for source in ("FERNET_KEY", "SECRET_KEY", "config", "missing"):
            self.assertFalse(sk.uses_random_secret_key({"SECRET_KEY_SOURCE": source}))
        self.assertFalse(sk.uses_random_secret_key({}))
        self.assertEqual(3, sk.key_length("abc"))
        self.assertEqual(4, sk.key_length("ññ"))
        self.assertEqual(4, sk.key_length(1234))


# ---------------------------------------------------------------------------
# Pure check per level
# ---------------------------------------------------------------------------


class TestCheckSecretKeys(KeyTestCase):
    @staticmethod
    def check(
        level,
        token_key=KEY_A,
        source="FERNET_KEY",
        keys_differ=False,
        bi_key=BI_KEY,
        mfa_enabled=False,
    ):
        warnings, errors = sk.check_secret_keys(
            level=level,
            token_key=token_key,
            source=source,
            keys_differ=keys_differ,
            bi_key=bi_key,
            mfa_enabled=mfa_enabled,
        )
        return tuple(warnings), tuple(errors)

    def assertResult(self, result, warnings=(), errors=()):
        self.assertEqual((tuple(warnings), tuple(errors)), result)
        for message in (*result[0], *result[1]):
            self.assertNoKeyValue(message, "R" * 64)

    def test_valid_keys_give_no_message(self):
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertResult(self.check(level))
                self.assertResult(
                    self.check(level, token_key=L32, source="SECRET_KEY", bi_key=BI_32)
                )

    def test_random_key(self):
        random_key = "R" * 64
        for mfa_enabled in (False, True):
            with self.subTest(level=1, mfa_enabled=mfa_enabled):
                self.assertResult(
                    self.check(
                        1, token_key=random_key, source="random", mfa_enabled=mfa_enabled
                    ),
                    warnings=(sk.random_key_warning(mfa_enabled),),
                )
        for level in (2, 3):
            with self.subTest(level=level):
                self.assertResult(
                    self.check(level, token_key=random_key, source="random"),
                    errors=(sk.missing_key_error(level),),
                )

    def test_random_key_message_mentions_mfa_only_with_mfa(self):
        without_mfa = sk.random_key_warning(False)
        with_mfa = sk.random_key_warning(True)
        self.assertNotIn("MFA", without_mfa)
        self.assertIn("MFA_ENABLED=1", with_mfa)
        self.assertIn("DELETE /user/<id>/mfa/", with_mfa)
        for message in (without_mfa, with_mfa):
            self.assertIn("FERNET_KEY", message)
            self.assertIn(sk.GENERATE_KEY_HINT, message)

    def test_missing_key(self):
        cases = (
            {"token_key": None, "source": "missing"},
            {"token_key": None, "source": "config"},
            {"token_key": "", "source": "config"},
            {"token_key": KEY_A, "source": "missing"},
        )
        for case in cases:
            with self.subTest(level=1, **case):
                self.assertResult(
                    self.check(1, **case), warnings=(sk.TOKEN_KEY_MISSING_WARNING,)
                )
            for level in (2, 3):
                with self.subTest(level=level, **case):
                    self.assertResult(
                        self.check(level, **case), errors=(sk.missing_key_error(level),)
                    )

    def test_short_signing_key(self):
        cases = (
            ("FERNET_KEY", SHORT, "FERNET_KEY"),
            ("FERNET_KEY", L31, "FERNET_KEY"),
            ("SECRET_KEY", SHORT, "SECRET_KEY"),
            ("SECRET_KEY", L31, "SECRET_KEY"),
            ("config", SHORT, "SECRET_TOKEN_KEY"),
        )
        for source, key, label in cases:
            with self.subTest(level=1, source=source, length=len(key)):
                self.assertResult(
                    self.check(1, token_key=key, source=source),
                    warnings=(sk.short_key_warning(label),),
                )
            for level in (2, 3):
                with self.subTest(level=level, source=source, length=len(key)):
                    self.assertResult(
                        self.check(level, token_key=key, source=source),
                        errors=(sk.short_key_error(level, label),),
                    )

    def test_signing_key_of_32_bytes_is_accepted(self):
        for source in ("FERNET_KEY", "SECRET_KEY", "config"):
            for level in LEVELS:
                with self.subTest(level=level, source=source):
                    self.assertResult(self.check(level, token_key=L32, source=source))

    def test_length_is_measured_in_bytes(self):
        # 16 characters of 2 bytes each are 32 bytes
        key = "ñ" * 16
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertResult(self.check(level, token_key=key, source="config"))

    def test_short_key_messages_use_the_minimum_length(self):
        for message in (
            sk.short_key_warning("FERNET_KEY"),
            sk.short_key_error(2, "FERNET_KEY"),
            sk.missing_key_error(3),
            sk.bi_key_short_warning(),
            sk.bi_key_short_error(2),
        ):
            with self.subTest(message=message[:30]):
                self.assertIn("32 bytes", message)
                self.assertIn(sk.GENERATE_KEY_HINT, message)
        self.assertIn("256 bits", sk.missing_key_error(2))
        self.assertIn("Security level 3", sk.missing_key_error(3))
        self.assertIn("FERNET_KEY is shorter", sk.short_key_warning("FERNET_KEY"))
        self.assertIn("SECRET_KEY is shorter", sk.short_key_warning("SECRET_KEY"))
        self.assertIn("but SECRET_KEY is shorter", sk.short_key_error(2, "SECRET_KEY"))

    def test_keys_differ(self):
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertResult(
                    self.check(level, keys_differ=True),
                    warnings=(sk.KEYS_DIFFER_WARNING,),
                )

    def test_bi_key(self):
        for level in LEVELS:
            for bi_key in (None, ""):
                with self.subTest(level=level, bi_key=bi_key):
                    self.assertResult(
                        self.check(level, bi_key=bi_key),
                        warnings=(sk.BI_KEY_MISSING_WARNING,),
                    )
            with self.subTest(level=level, bi_key="32 bytes"):
                self.assertResult(self.check(level, bi_key=BI_32))
        with self.subTest(level=1, bi_key="23 bytes"):
            self.assertResult(
                self.check(1, bi_key=BI_23), warnings=(sk.bi_key_short_warning(),)
            )
        for level in (2, 3):
            with self.subTest(level=level, bi_key="23 bytes"):
                self.assertResult(
                    self.check(level, bi_key=BI_23),
                    errors=(sk.bi_key_short_error(level),),
                )

    def test_short_signing_key_and_short_bi_key_give_two_errors_in_order(self):
        for level in (2, 3):
            with self.subTest(level=level):
                self.assertResult(
                    self.check(level, token_key=SHORT, bi_key=BI_23),
                    errors=(
                        sk.short_key_error(level, "FERNET_KEY"),
                        sk.bi_key_short_error(level),
                    ),
                )

    def test_warnings_are_ordered_signing_key_differ_bi_key(self):
        self.assertResult(
            self.check(1, token_key=SHORT, keys_differ=True, bi_key=None),
            warnings=(
                sk.short_key_warning("FERNET_KEY"),
                sk.KEYS_DIFFER_WARNING,
                sk.BI_KEY_MISSING_WARNING,
            ),
        )
        self.assertResult(
            self.check(1, token_key=SHORT, keys_differ=True, bi_key=BI_23),
            warnings=(
                sk.short_key_warning("FERNET_KEY"),
                sk.KEYS_DIFFER_WARNING,
                sk.bi_key_short_warning(),
            ),
        )

    def test_differ_warning_does_not_turn_into_an_error(self):
        for level in (2, 3):
            with self.subTest(level=level):
                self.assertResult(
                    self.check(level, keys_differ=True, bi_key=None),
                    warnings=(sk.KEYS_DIFFER_WARNING, sk.BI_KEY_MISSING_WARNING),
                )

    def test_api_key_and_ephemeral_texts(self):
        self.assertIn("User 7", sk.api_key_random_key_warning(7))
        self.assertIn("FERNET_KEY", sk.api_key_random_key_warning(7))
        self.assertIn("ana", sk.cli_api_key_random_key_warning("ana"))
        self.assertIn("FERNET_KEY", sk.cli_api_key_random_key_warning("ana"))
        self.assertIn("CORNFLOW_EPHEMERAL_SECRET_KEY", sk.EPHEMERAL_KEY_SHARED_INFO)


class TestGenerateKeyHint(KeyTestCase):
    """The command that the messages suggest to generate a key."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The code of the command, not GENERATE_KEY_HINT: the generated key
        # tests do not depend on the text of the constant.
        cls.key, cls.bi = (
            subprocess.run(
                [sys.executable, "-I", "-c", FERNET_KEY_CODE],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            ).stdout.strip()
            for _ in range(2)
        )

    def test_hint_is_the_fernet_command(self):
        self.assertEqual(FERNET_KEY_COMMAND, sk.GENERATE_KEY_HINT)
        self.assertIn("Fernet.generate_key", sk.GENERATE_KEY_HINT)
        self.assertNotIn("token_hex", sk.GENERATE_KEY_HINT)

    def test_key_messages_suggest_the_fernet_command(self):
        messages = {
            "missing_key_error(2)": sk.missing_key_error(2),
            "missing_key_error(3)": sk.missing_key_error(3),
            "short_key_error(2)": sk.short_key_error(2, "FERNET_KEY"),
            "short_key_error(3)": sk.short_key_error(3, "SECRET_KEY"),
            "random_key_warning(False)": sk.random_key_warning(False),
            "random_key_warning(True)": sk.random_key_warning(True),
            "short_key_warning(FERNET_KEY)": sk.short_key_warning("FERNET_KEY"),
            "short_key_warning(SECRET_KEY)": sk.short_key_warning("SECRET_KEY"),
            "short_key_warning(SECRET_TOKEN_KEY)": sk.short_key_warning(
                "SECRET_TOKEN_KEY"
            ),
            "bi_key_short_warning()": sk.bi_key_short_warning(),
            "bi_key_short_error(2)": sk.bi_key_short_error(2),
            "bi_key_short_error(3)": sk.bi_key_short_error(3),
        }
        for name, message in messages.items():
            with self.subTest(message=name):
                self.assertEqual(1, message.count(FERNET_KEY_COMMAND))
                self.assertNotIn("token_hex", message)
                self.assertNoKeyValue(message)

    def test_startup_messages_suggest_the_fernet_command(self):
        exc, _ = start_fails(self, 2, {})
        self.assertIn(FERNET_KEY_COMMAND, exc.error)
        self.assertNotIn("token_hex", exc.error)
        _, handler = start(1, {})
        lines = key_lines(handler)
        self.assertTrue(any(FERNET_KEY_COMMAND in line for line in lines), lines)
        for line in lines:
            self.assertNotIn("token_hex", line)

    def test_generated_key_is_a_fernet_key_of_32_bytes(self):
        for key in (self.key, self.bi):
            with self.subTest(key_length=len(key)):
                self.assertRegex(key, r"^[A-Za-z0-9_-]{43}=$")
                self.assertEqual(44, len(key))
                self.assertEqual(32, len(base64.urlsafe_b64decode(key)))
                self.assertGreaterEqual(
                    sk.key_length(key), sk.MINIMUM_SECRET_KEY_LENGTH
                )
                fernet = Fernet(key.encode())
                self.assertEqual(b"cornflow", fernet.decrypt(fernet.encrypt(b"cornflow")))
        self.assertNotEqual(self.key, self.bi)

    def test_generated_key_is_accepted_at_every_level(self):
        key, bi = self.key, self.bi
        for level in LEVELS:
            with self.subTest(level=level):
                resolved = sk.resolve_secret_keys(
                    {"FERNET_KEY": key, "SECRET_BI_KEY": bi}, level
                )
                self.assertEqual("FERNET_KEY", resolved.source)
                self.assertEqual(key, resolved.token_key)
                self.assertIs(False, resolved.keys_differ)
                self.assertEqual(
                    ((), ()),
                    tuple(
                        tuple(x)
                        for x in sk.check_secret_keys(
                            level=level,
                            token_key=key,
                            source="FERNET_KEY",
                            keys_differ=False,
                            bi_key=bi,
                            mfa_enabled=False,
                        )
                    ),
                )
                app, handler = start(level, {"FERNET_KEY": key, "SECRET_BI_KEY": bi})
                self.assertEqual([], key_lines(handler))
                self.assertEqual(key, app.config["SECRET_TOKEN_KEY"])


# ---------------------------------------------------------------------------
# create_app
# ---------------------------------------------------------------------------


class TestSecretKeysAtStartup(KeyTestCase):
    def test_fernet_key_is_used(self):
        for level in LEVELS:
            with self.subTest(level=level, keys="both"):
                app, handler = start(
                    level,
                    {"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_B, "SECRET_BI_KEY": BI_KEY},
                )
                self.assertEqual(KEY_A, app.config["SECRET_TOKEN_KEY"])
                self.assertEqual("FERNET_KEY", app.config["SECRET_KEY_SOURCE"])
                self.assertEqual([sk.KEYS_DIFFER_WARNING], key_lines(handler))
                for line in handler.lines():
                    self.assertNoKeyValue(line)
            with self.subTest(level=level, keys="equal"):
                app, handler = start(
                    level,
                    {"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY},
                )
                self.assertEqual(KEY_A, app.config["SECRET_TOKEN_KEY"])
                self.assertEqual([], key_lines(handler))

    def test_secret_key_is_used_without_fernet_key(self):
        for level in LEVELS:
            with self.subTest(level=level):
                app, handler = start(
                    level, {"SECRET_KEY": KEY_B, "SECRET_BI_KEY": BI_KEY}
                )
                self.assertEqual(KEY_B, app.config["SECRET_TOKEN_KEY"])
                self.assertEqual("SECRET_KEY", app.config["SECRET_KEY_SOURCE"])
                self.assertEqual([], key_lines(handler))

    def test_no_key_by_level(self):
        keys = {"SECRET_BI_KEY": BI_KEY}
        for mfa_enabled in (0, 1):
            with self.subTest(level=1, mfa_enabled=mfa_enabled):
                app, handler = start(1, keys, MFA_ENABLED=mfa_enabled)
                self.assertEqual("random", app.config["SECRET_KEY_SOURCE"])
                self.assertRegex(app.config["SECRET_TOKEN_KEY"], r"^[0-9a-f]{64}$")
                self.assertEqual(
                    [sk.random_key_warning(bool(mfa_enabled))], key_lines(handler)
                )
                for line in handler.lines():
                    self.assertNoKeyValue(line, app.config["SECRET_TOKEN_KEY"])
        for level in (2, 3):
            for mfa_enabled in (0, 1):
                with self.subTest(level=level, mfa_enabled=mfa_enabled):
                    exc, _ = start_fails(self, level, keys, MFA_ENABLED=mfa_enabled)
                    self.assertEqual(sk.missing_key_error(level), exc.error)

    def test_ephemeral_key_is_not_a_fixed_key(self):
        ephemeral = "E" * 64
        app, handler = start(
            1, {"CORNFLOW_EPHEMERAL_SECRET_KEY": ephemeral, "SECRET_BI_KEY": BI_KEY}
        )
        self.assertEqual(ephemeral, app.config["SECRET_TOKEN_KEY"])
        self.assertEqual("random", app.config["SECRET_KEY_SOURCE"])
        self.assertEqual([sk.random_key_warning(False)], key_lines(handler))
        for line in handler.lines():
            self.assertNotIn(ephemeral, line)

    def test_short_key_by_level(self):
        cases = (
            ({"FERNET_KEY": SHORT}, "FERNET_KEY"),
            ({"FERNET_KEY": L31}, "FERNET_KEY"),
            ({"SECRET_KEY": SHORT}, "SECRET_KEY"),
        )
        for keys, label in cases:
            environ = dict(keys, SECRET_BI_KEY=BI_KEY)
            with self.subTest(level=1, keys=sorted(keys), length=len(*keys.values())):
                app, handler = start(1, environ)
                self.assertEqual([sk.short_key_warning(label)], key_lines(handler))
                for line in handler.lines():
                    self.assertNoKeyValue(line, L31)
            for level in (2, 3):
                with self.subTest(
                    level=level, keys=sorted(keys), length=len(*keys.values())
                ):
                    exc, _ = start_fails(self, level, environ)
                    self.assertEqual(sk.short_key_error(level, label), exc.error)
                    self.assertNoKeyValue(exc.error, L31)
        for level in LEVELS:
            for variable in ("FERNET_KEY", "SECRET_KEY"):
                with self.subTest(level=level, length=32, variable=variable):
                    app, handler = start(level, {variable: L32, "SECRET_BI_KEY": BI_KEY})
                    self.assertEqual(L32, app.config["SECRET_TOKEN_KEY"])
                    self.assertEqual([], key_lines(handler))

    def test_bi_key_by_level(self):
        fernet = {"FERNET_KEY": KEY_A}
        for level in LEVELS:
            for name, bi_environ in (("unset", {}), ("empty", {"SECRET_BI_KEY": ""})):
                with self.subTest(level=level, bi_key=name):
                    app, handler = start(level, {**fernet, **bi_environ})
                    self.assertEqual([sk.BI_KEY_MISSING_WARNING], key_lines(handler))
                    self.assertFalse(app.config["SECRET_BI_KEY"])
            with self.subTest(level=level, bi_key="32 bytes"):
                app, handler = start(level, {**fernet, "SECRET_BI_KEY": BI_32})
                self.assertEqual([], key_lines(handler))
        with self.subTest(level=1, bi_key="23 bytes"):
            app, handler = start(1, {**fernet, "SECRET_BI_KEY": BI_23})
            self.assertEqual([sk.bi_key_short_warning()], key_lines(handler))
            for line in handler.lines():
                self.assertNotIn(BI_23, line)
        for level in (2, 3):
            with self.subTest(level=level, bi_key="23 bytes"):
                exc, _ = start_fails(self, level, {**fernet, "SECRET_BI_KEY": BI_23})
                self.assertEqual(sk.bi_key_short_error(level), exc.error)
                self.assertNotIn(BI_23, exc.error)

    def test_every_error_is_reported_joined(self):
        exc, _ = start_fails(
            self, 2, {"FERNET_KEY": SHORT, "SECRET_BI_KEY": BI_23}
        )
        self.assertEqual(
            "; ".join(
                (sk.short_key_error(2, "FERNET_KEY"), sk.bi_key_short_error(2))
            ),
            exc.error,
        )

    def test_check_order(self):
        # The disabling zeros are checked before the keys
        exc, _ = start_fails(self, 2, {}, LOGIN_MAX_ATTEMPTS=0)
        self.assertIn("LOGIN_MAX_ATTEMPTS=0", exc.error)
        self.assertNotIn("secret key", exc.error)
        # and the keys before the coherence of MFA
        exc, _ = start_fails(self, 2, {}, MFA_REQUIRED=1)
        self.assertEqual(sk.missing_key_error(2), exc.error)
        self.assertNotIn("MFA_ENABLED", exc.error)

    def test_testing_config_has_no_key_warnings(self):
        with capture_log() as handler:
            app = create_app("testing")
        self.assertEqual("config", app.config["SECRET_KEY_SOURCE"])
        self.assertFalse(app.config["SECRET_KEYS_DIFFER"])
        self.assertEqual(TESTING_TOKEN_KEY, app.config["SECRET_TOKEN_KEY"])
        self.assertEqual([], key_lines(handler))

    def test_a_config_without_key_metadata_is_treated_as_level_1_config(self):
        from cornflow.app import _check_secret_keys

        app = Flask(__name__)
        app.config["SECRET_TOKEN_KEY"] = L32
        app.config["SECRET_BI_KEY"] = L32
        with self.assertNoLogs(app.logger, "WARNING"):
            _check_secret_keys(app)

        app = Flask(__name__)
        app.config["SECRET_TOKEN_KEY"] = SHORT
        app.config["SECRET_BI_KEY"] = L32
        with self.assertLogs(app.logger, "WARNING") as logs:
            _check_secret_keys(app)
        self.assertEqual(
            [sk.short_key_warning("SECRET_TOKEN_KEY")],
            [record.getMessage() for record in logs.records],
        )

    def test_minimum_length_is_still_exported_by_app(self):
        from cornflow.app import MINIMUM_SECRET_KEY_LENGTH

        self.assertEqual(32, MINIMUM_SECRET_KEY_LENGTH)
        self.assertEqual(sk.MINIMUM_SECRET_KEY_LENGTH, MINIMUM_SECRET_KEY_LENGTH)


# ---------------------------------------------------------------------------
# cornflow.config reading the real environment (subprocess)
# ---------------------------------------------------------------------------

_CONFIG_SCRIPT = """
import hashlib
import json
from cornflow.config import DefaultConfig, Production, Testing

def digest(value):
    return None if value is None else hashlib.sha256(value.encode("utf8")).hexdigest()

out = {}
for cls in (DefaultConfig, Production, Testing):
    out[cls.__name__] = {
        "source": cls.SECRET_KEY_SOURCE,
        "differ": cls.SECRET_KEYS_DIFFER,
        "token": digest(cls.SECRET_TOKEN_KEY),
        "has_bi": bool(cls.SECRET_BI_KEY),
    }
print(json.dumps(out))
"""


def sha256(value):
    import hashlib

    return hashlib.sha256(value.encode("utf8")).hexdigest()


def import_config(env_overrides):
    """
    Imports cornflow.config in a new interpreter whose environment has no key
    nor security level variable except the given ones.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in KEY_VARS and name != "CORNFLOW_SECURITY_LEVEL"
    }
    env.update(env_overrides)
    result = subprocess.run(
        [sys.executable, "-c", _CONFIG_SCRIPT],
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


class TestConfigReadsKeysFromEnvironment(KeyTestCase):
    SERVER_CLASSES = ("DefaultConfig", "Production")

    def assertServerConfig(self, config, source, token, differ=False):
        for name in self.SERVER_CLASSES:
            with self.subTest(config=name):
                self.assertEqual(source, config[name]["source"])
                self.assertEqual(differ, config[name]["differ"])
                self.assertEqual(token, config[name]["token"])

    def assertTestingConfig(self, config):
        self.assertEqual("config", config["Testing"]["source"])
        self.assertFalse(config["Testing"]["differ"])
        self.assertEqual(sha256(TESTING_TOKEN_KEY), config["Testing"]["token"])
        self.assertTrue(config["Testing"]["has_bi"])

    def test_fernet_key(self):
        config = import_config({"FERNET_KEY": KEY_A})
        self.assertServerConfig(config, "FERNET_KEY", sha256(KEY_A))
        self.assertFalse(config["DefaultConfig"]["has_bi"])
        self.assertTestingConfig(config)

    def test_fernet_key_wins_over_secret_key(self):
        config = import_config({"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_B})
        self.assertServerConfig(config, "FERNET_KEY", sha256(KEY_A), differ=True)
        self.assertTestingConfig(config)

    def test_secret_key_only(self):
        config = import_config({"SECRET_KEY": KEY_B})
        self.assertServerConfig(config, "SECRET_KEY", sha256(KEY_B))

    def test_empty_fernet_key_falls_back_to_secret_key(self):
        config = import_config({"FERNET_KEY": "", "SECRET_KEY": KEY_B})
        self.assertServerConfig(config, "SECRET_KEY", sha256(KEY_B))

    def test_bi_key_is_read(self):
        config = import_config({"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY})
        for name in self.SERVER_CLASSES:
            self.assertTrue(config[name]["has_bi"])

    def test_without_keys_the_key_is_random_and_different_each_time(self):
        first = import_config({})
        second = import_config({})
        for config in (first, second):
            for name in self.SERVER_CLASSES:
                self.assertEqual("random", config[name]["source"])
                self.assertIsNotNone(config[name]["token"])
            self.assertTestingConfig(config)
        # One key per process: DefaultConfig and Production share it
        self.assertEqual(
            first["DefaultConfig"]["token"], first["Production"]["token"]
        )
        self.assertNotEqual(
            first["DefaultConfig"]["token"], second["DefaultConfig"]["token"]
        )

    def test_ephemeral_key_is_shared(self):
        env = {"CORNFLOW_EPHEMERAL_SECRET_KEY": "E" * 64}
        for _ in range(2):
            config = import_config(env)
            self.assertServerConfig(config, "random", sha256("E" * 64))

    def test_fernet_key_wins_over_the_ephemeral_key(self):
        config = import_config(
            {"CORNFLOW_EPHEMERAL_SECRET_KEY": "E" * 64, "FERNET_KEY": KEY_A}
        )
        self.assertServerConfig(config, "FERNET_KEY", sha256(KEY_A))

    def test_level_2_without_keys_is_missing_and_import_does_not_fail(self):
        for level in ("2", "3"):
            with self.subTest(level=level):
                config = import_config(
                    {"CORNFLOW_SECURITY_LEVEL": level, "SECRET_BI_KEY": BI_KEY}
                )
                self.assertServerConfig(config, "missing", None)
                self.assertTrue(config["DefaultConfig"]["has_bi"])
                self.assertTestingConfig(config)

    def test_level_2_ignores_the_ephemeral_key(self):
        config = import_config(
            {"CORNFLOW_SECURITY_LEVEL": "2", "CORNFLOW_EPHEMERAL_SECRET_KEY": "E" * 64}
        )
        self.assertServerConfig(config, "missing", None)

    def test_level_2_with_a_key(self):
        config = import_config({"CORNFLOW_SECURITY_LEVEL": "2", "FERNET_KEY": KEY_A})
        self.assertServerConfig(config, "FERNET_KEY", sha256(KEY_A))


# ---------------------------------------------------------------------------
# Several applications over the same database
# ---------------------------------------------------------------------------


class _DatabaseMixin:
    """
    Applications created with different keys over the same SQLite database
    (the one of Testing). The user "ana" is created by the first application.
    """

    level = 1
    username = "ana"

    def make_app(self, key_environ, **overrides):
        name = security_level_config(
            self.level,
            key_environ=key_environ,
            **level_overrides(self.level, **overrides),
        )
        return create_app(name)

    database_app = None

    def prepare_database(self, app):
        self.drop_database()
        self.database_app = app
        with app.app_context():
            db.drop_all()
            db.create_all()
            access_init_command(verbose=False)
            user = UserModel(
                {
                    "username": self.username,
                    "email": f"{self.username}@test.com",
                    "password": PASSWORD,
                }
            )
            user.save()
            UserRoleModel({"user_id": user.id, "role_id": PLANNER_ROLE}).save()
            self.user_id = user.id
        self.addCleanup(self.drop_database)

    def drop_database(self):
        app, self.database_app = self.database_app, None
        if app is None:
            return
        with app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def login(app, username="ana"):
        with app.app_context():
            response = app.test_client().post(
                LOGIN_URL, json={"username": username, "password": PASSWORD}
            )
            assert response.status_code == 200, response.json
            return response.json["token"]

    @staticmethod
    def get_instances(app, token):
        with app.app_context():
            return app.test_client().get(
                INSTANCE_URL, headers={"Authorization": f"Bearer {token}"}
            )


class _TokensAcrossAppsTests(_DatabaseMixin):
    def test_token_follows_fernet_key(self):
        x = self.make_app({"FERNET_KEY": KEY_A, "SECRET_KEY": KEY_B})
        self.prepare_database(x)
        token = self.login(x)
        self.assertEqual(200, self.get_instances(x, token).status_code)

        y = self.make_app({"FERNET_KEY": KEY_A})
        self.assertEqual(200, self.get_instances(y, token).status_code)

        z = self.make_app({"SECRET_KEY": KEY_B})
        self.assertIn(self.get_instances(z, token).status_code, (400, 401))

    def test_empty_fernet_key_falls_back(self):
        x = self.make_app({"FERNET_KEY": "", "SECRET_KEY": KEY_B})
        self.prepare_database(x)
        token = self.login(x)
        y = self.make_app({"SECRET_KEY": KEY_B})
        self.assertEqual(200, self.get_instances(y, token).status_code)

    def test_encrypted_secret_survives_with_same_key(self):
        x = self.make_app({"FERNET_KEY": KEY_A})
        with x.app_context():
            encrypted = encrypt_value("JBSWY3DP")
        self.assertNotIn("JBSWY3DP", encrypted)

        y = self.make_app({"FERNET_KEY": KEY_A})
        with y.app_context():
            self.assertEqual("JBSWY3DP", decrypt_value(encrypted))

        z = self.make_app({"SECRET_KEY": KEY_B})
        with z.app_context():
            with self.assertRaises(InvalidUsage) as ctx:
                decrypt_value(encrypted)
        self.assertEqual(500, ctx.exception.status_code)
        self.assertIn("FERNET_KEY", ctx.exception.log_txt)
        self.assertIn("DELETE /user/<id>/mfa/", ctx.exception.log_txt)
        self.assertNotIn(KEY_A, ctx.exception.log_txt)
        self.assertNotIn(KEY_B, ctx.exception.log_txt)

class TestEncryptionWithoutKey(unittest.TestCase):
    def test_encryption_without_key(self):
        app = Flask(__name__)
        app.config["SECRET_TOKEN_KEY"] = None
        with app.app_context():
            with self.assertRaises(ConfigurationError) as ctx:
                encrypt_value("JBSWY3DP")
        for text in (ctx.exception.error, str(ctx.exception)):
            self.assertIn("FERNET_KEY", text)
            self.assertIn("SECRET_KEY", text)


class TestTokensAcrossAppsLevel1(_TokensAcrossAppsTests, unittest.TestCase):
    level = 1


class TestTokensAcrossAppsLevel3(_TokensAcrossAppsTests, unittest.TestCase):
    level = 3


# ---------------------------------------------------------------------------
# cornflow service init
# ---------------------------------------------------------------------------


def _fake_initialize_database(app, external_app_module=None):
    """Replaces the Alembic migrations, which do not run on SQLite."""
    with app.app_context():
        db.create_all()
        access_init_command(verbose=False)


class TestServiceInitSecretKey(TestCase):
    ADMIN_PWD = "Granito-Vela-Oruga7"
    SERVICE_PWD = "Mimbre-Faro-Ciervo4"

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def run_init(self, level, key_environ):
        """
        Runs `cornflow service init` with the keys of key_environ both in the
        configuration class and in the environment of the operator. Returns
        (result, os.system mock, copy of os.environ when gunicorn starts, name
        of the configuration, os.environ after the command).
        """
        name = security_level_config(
            level, key_environ=key_environ, **level_overrides(level)
        )
        env = {
            "FLASK_ENV": name,
            "CORNFLOW_BACKEND": "1",
            "AUTH_TYPE": "1",
            "CORNFLOW_ADMIN_PWD": self.ADMIN_PWD,
            "CORNFLOW_SERVICE_PWD": self.SERVICE_PWD,
        }
        env.update(key_environ)
        uri = app_config[name].SQLALCHEMY_DATABASE_URI
        gunicorn_env = []

        def fake_system(command, *args, **kwargs):
            if "gunicorn" in str(command):
                gunicorn_env.append(dict(os.environ))
            return 0

        # import_module: the attribute cornflow.cli.service is the click group
        service_module = importlib.import_module("cornflow.cli.service")
        with mock.patch.dict(os.environ, env):
            for variable in KEY_VARS:
                if variable not in key_environ:
                    os.environ.pop(variable, None)
            os.environ.pop("SIGNUP_ACTIVATED", None)
            with mock.patch.object(service_module.os, "chdir"), mock.patch.object(
                service_module, "get_db_conn", return_value=uri
            ), mock.patch.object(
                service_module, "_sync_with_airflow"
            ), mock.patch.object(
                service_module,
                "_initialize_database",
                side_effect=_fake_initialize_database,
            ), mock.patch.object(
                service_module.os, "system", side_effect=fake_system
            ) as system:
                with capture_log(SERVICE_LOGGER, logging.INFO) as handler:
                    result = CliRunner().invoke(cli, ["service", "init"])
                after = dict(os.environ)
        self.logs = handler.lines()
        return result, system, (gunicorn_env or [None])[0], name, after

    def test_level_1_without_key_shares_one_key(self):
        keys = {"SECRET_BI_KEY": BI_KEY}
        result, system, gunicorn_env, name, _ = self.run_init(1, keys)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIsNotNone(gunicorn_env, "gunicorn was not started")
        shared = gunicorn_env.get("CORNFLOW_EPHEMERAL_SECRET_KEY")
        self.assertTrue(shared)
        self.assertNotIn("FERNET_KEY", gunicorn_env)
        self.assertNotIn("SECRET_KEY", gunicorn_env)
        # It is the key of the application of init
        self.assertEqual(app_config[name].SECRET_TOKEN_KEY, shared)
        self.assertTrue(
            any(sk.EPHEMERAL_KEY_SHARED_INFO in line for line in self.logs), self.logs
        )
        for line in self.logs:
            self.assertNotIn(shared, line)
        self.assertNotIn(shared, result.output)

        # The workers read the same environment: same key, none generated
        worker_keys = {
            variable: gunicorn_env[variable]
            for variable in KEY_VARS
            if variable in gunicorn_env
        }
        with mock.patch(
            "cornflow.shared.secret_keys.generate_secret_key"
        ) as generate:
            worker_1 = build_security_level_config(
                1, key_environ=worker_keys, **level_overrides(1)
            )
            worker_2 = build_security_level_config(
                1, key_environ=worker_keys, **level_overrides(1)
            )
        generate.assert_not_called()
        self.assertEqual(shared, worker_1.SECRET_TOKEN_KEY)
        self.assertEqual(worker_1.SECRET_TOKEN_KEY, worker_2.SECRET_TOKEN_KEY)

        with mock.patch.dict(
            app_config, {"t003-worker-1": worker_1, "t003-worker-2": worker_2}
        ):
            app_1 = create_app("t003-worker-1")
            app_2 = create_app("t003-worker-2")
        user_id = UserModel.get_one_user_by_username("cornflow_admin").id
        with app_1.app_context():
            token = Auth.generate_token(user_id)
        with app_2.app_context():
            self.assertEqual("cornflow_admin", Auth.decode_token(token)["sub"])

    def test_levels_2_and_3_without_key_do_not_start(self):
        for level in (2, 3):
            with self.subTest(level=level):
                result, system, gunicorn_env, _, after = self.run_init(
                    level, {"SECRET_BI_KEY": BI_KEY}
                )
                self.assertNotEqual(0, result.exit_code)
                self.assertIn(sk.missing_key_error(level), result.output)
                self.assertEqual(0, UserModel.query.count())
                self.assertIsNone(gunicorn_env)
                self.assertFalse(
                    any("gunicorn" in str(call.args[0]) for call in system.call_args_list)
                )
                self.assertNotIn("CORNFLOW_EPHEMERAL_SECRET_KEY", after)

    def test_levels_2_and_3_with_a_short_key_do_not_start(self):
        for level in (2, 3):
            with self.subTest(level=level):
                result, _, gunicorn_env, _, _ = self.run_init(
                    level, {"FERNET_KEY": SHORT, "SECRET_BI_KEY": BI_KEY}
                )
                self.assertNotEqual(0, result.exit_code)
                self.assertIn(sk.short_key_error(level, "FERNET_KEY"), result.output)
                self.assertNotIn(SHORT, result.output)
                self.assertIsNone(gunicorn_env)

    def test_init_does_not_write_keys(self):
        for level in LEVELS:
            with self.subTest(level=level, keys="FERNET_KEY"):
                keys = {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}
                result, _, gunicorn_env, _, _ = self.run_init(level, keys)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertNotIn("SECRET_KEY", gunicorn_env)
                self.assertNotIn("CORNFLOW_EPHEMERAL_SECRET_KEY", gunicorn_env)
                self.assertEqual(KEY_A, gunicorn_env["FERNET_KEY"])
                self.assertFalse(
                    any(sk.EPHEMERAL_KEY_SHARED_INFO in line for line in self.logs)
                )
            self.drop_users()
            with self.subTest(level=level, keys="both"):
                keys = {
                    "FERNET_KEY": KEY_A,
                    "SECRET_KEY": KEY_B,
                    "SECRET_BI_KEY": BI_KEY,
                }
                result, _, gunicorn_env, _, _ = self.run_init(level, keys)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertEqual(KEY_A, gunicorn_env["FERNET_KEY"])
                self.assertEqual(KEY_B, gunicorn_env["SECRET_KEY"])
                self.assertNotIn("CORNFLOW_EPHEMERAL_SECRET_KEY", gunicorn_env)
            self.drop_users()

    def test_init_with_secret_key_only_keeps_it(self):
        keys = {"SECRET_KEY": KEY_B, "SECRET_BI_KEY": BI_KEY}
        result, _, gunicorn_env, _, _ = self.run_init(1, keys)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(KEY_B, gunicorn_env["SECRET_KEY"])
        self.assertNotIn("FERNET_KEY", gunicorn_env)
        self.assertNotIn("CORNFLOW_EPHEMERAL_SECRET_KEY", gunicorn_env)

    def drop_users(self):
        db.session.remove()
        db.drop_all()
        db.create_all()

    def test_setup_environment_does_not_touch_keys(self):
        from cornflow.cli.service import _setup_environment_variables

        service_module = importlib.import_module("cornflow.cli.service")

        base = {"PATH": os.environ.get("PATH", ""), "CORNFLOW_BACKEND": "1"}
        for extra in ({}, {"SECRET_KEY": KEY_B}):
            with self.subTest(extra=sorted(extra)):
                with mock.patch.dict(os.environ, {**base, **extra}, clear=True):
                    with mock.patch.object(
                        service_module, "get_db_conn", return_value="sqlite://"
                    ):
                        _setup_environment_variables()
                    after = dict(os.environ)
                for variable in KEY_VARS:
                    self.assertEqual(extra.get(variable), after.get(variable), variable)

    def test_service_module_has_no_key_generation(self):
        # import_module: the attribute cornflow.cli.service is the click group
        service_module = importlib.import_module("cornflow.cli.service")

        with open(service_module.__file__, encoding="utf-8") as handler:
            source = handler.read()
        self.assertNotIn("Fernet", source)
        self.assertIsNone(re.search(r'setdefault\(\s*"SECRET_KEY"', source))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def last_line(text):
    return [line for line in text.strip().splitlines() if line.strip()][-1].strip()


class _CliTests(_DatabaseMixin):
    def run_cli(self, args, key_environ, **overrides):
        name = security_level_config(
            self.level, key_environ=key_environ, **level_overrides(self.level, **overrides)
        )
        env = {
            "FLASK_ENV": name,
            "DATABASE_URL": app_config[name].SQLALCHEMY_DATABASE_URI,
            "EXTERNAL_APP": "0",
        }
        with mock.patch.dict(os.environ, env):
            with capture_log() as handler:
                result = CliRunner().invoke(cli, args)
        return result, handler


class TestCliUsesServerKey(_CliTests, unittest.TestCase):
    def check_api_key(self, key_environ):
        for level in LEVELS:
            self.level = level
            with self.subTest(level=level, keys=sorted(key_environ)):
                server = self.make_app(key_environ)
                self.prepare_database(server)
                result, _ = self.run_cli(["users", "api_key", "-u", "ana"], key_environ)
                self.assertEqual(0, result.exit_code, result.output)
                api_key = last_line(result.output)
                self.assertEqual(200, self.get_instances(server, api_key).status_code)
                self.drop_database()

    def test_api_key_with_fernet_key(self):
        self.check_api_key({"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY})

    def test_api_key_with_secret_key(self):
        self.check_api_key({"SECRET_KEY": KEY_B, "SECRET_BI_KEY": BI_KEY})

    def test_bi_token_is_valid_in_the_server(self):
        keys = {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}
        for level in LEVELS:
            self.level = level
            with self.subTest(level=level):
                server = self.make_app(keys)
                self.prepare_database(server)
                result, _ = self.run_cli(
                    ["users", "bi_token", "-u", "ana"], keys, BI_TOKEN_DURATION_DAYS=30
                )
                self.assertEqual(0, result.exit_code, result.output)
                token = last_line(result.output)
                with server.app_context():
                    BIAuth.decode_token(token)
                self.drop_database()

    def test_subprocess_reads_the_real_environment(self):
        for variable, value in (("FERNET_KEY", KEY_A), ("SECRET_KEY", KEY_B)):
            with self.subTest(variable=variable):
                with tempfile.TemporaryDirectory() as folder:
                    uri = "sqlite:///" + os.path.join(folder, "cornflow.db")
                    name = "t003-subprocess-" + variable
                    config = build_security_level_config(
                        1,
                        key_environ={variable: value, "SECRET_BI_KEY": BI_KEY},
                        SQLALCHEMY_DATABASE_URI=uri,
                    )
                    with mock.patch.dict(app_config, {name: config}):
                        server = create_app(name)
                    self.prepare_database(server)

                    env = {
                        key: val
                        for key, val in os.environ.items()
                        if key not in KEY_VARS and key != "CORNFLOW_SECURITY_LEVEL"
                    }
                    env.update(
                        {
                            "FLASK_ENV": "development",
                            "DATABASE_URL": uri,
                            "EXTERNAL_APP": "0",
                            variable: value,
                        }
                    )
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            "from cornflow.cli import cli; cli()",
                            "users",
                            "api_key",
                            "-u",
                            "ana",
                        ],
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr[-2000:])
                    api_key = last_line(completed.stdout)
                    self.assertEqual(
                        200, self.get_instances(server, api_key).status_code
                    )
                    self.drop_database()


class TestApiKeyRandomKeyWarning(_CliTests, unittest.TestCase):
    level = 1

    def post_api_key(self, key_environ):
        app = self.make_app(key_environ)
        self.prepare_database(app)
        with capture_log() as handler:
            token = self.login(app)
            with app.app_context():
                response = app.test_client().post(
                    API_KEY_URL,
                    json={},
                    headers={"Authorization": f"Bearer {token}"},
                )
        return app, response, handler

    def test_endpoint_with_random_key_warns(self):
        app, response, handler = self.post_api_key({"SECRET_BI_KEY": BI_KEY})
        self.assertEqual(201, response.status_code, response.json)
        self.assertIn(
            sk.api_key_random_key_warning(self.user_id), handler.lines(logging.WARNING)
        )
        api_key = response.json["api_key"]
        for line in handler.lines():
            self.assertNotIn(api_key, line)
            self.assertNotIn(app.config["SECRET_TOKEN_KEY"], line)

    def test_endpoint_with_fixed_key_does_not_warn(self):
        _, response, handler = self.post_api_key(
            {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}
        )
        self.assertEqual(201, response.status_code, response.json)
        self.assertNotIn(
            sk.api_key_random_key_warning(self.user_id), handler.lines(logging.WARNING)
        )

    def test_cli_with_random_key_warns_and_the_key_is_not_valid_in_the_server(self):
        # The server is another process: it has its own random key
        server_config = build_security_level_config(
            1, key_environ={"SECRET_BI_KEY": BI_KEY}
        )
        with mock.patch.dict(app_config, {"t003-server-random": server_config}):
            server = create_app("t003-server-random")
        self.prepare_database(server)

        result, handler = self.run_cli(
            ["users", "api_key", "-u", "ana"], {"SECRET_BI_KEY": BI_KEY}
        )
        self.assertEqual(0, result.exit_code, result.output)
        api_key = last_line(result.output)
        self.assertIn(
            sk.cli_api_key_random_key_warning("ana"), handler.lines(logging.WARNING)
        )
        for line in handler.lines():
            self.assertNotIn(api_key, line)
        with server.app_context():
            with self.assertRaises(InvalidCredentials):
                Auth.decode_token(api_key)

    def test_cli_with_fixed_key_does_not_warn(self):
        keys = {"FERNET_KEY": KEY_A, "SECRET_BI_KEY": BI_KEY}
        server = self.make_app(keys)
        self.prepare_database(server)
        result, handler = self.run_cli(["users", "api_key", "-u", "ana"], keys)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn(
            sk.cli_api_key_random_key_warning("ana"), handler.lines(logging.WARNING)
        )


if __name__ == "__main__":
    unittest.main()
