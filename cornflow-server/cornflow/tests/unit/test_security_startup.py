"""
Tests of the startup checks that depend on the security level: invalid level,
disabling zeros the level does not allow, coherence of MFA_ENABLED, the startup
log, the level not being exposed, the session windows per level and
``cornflow service init`` (SIGNUP_ACTIVATED and default passwords).

The expected messages are written in this file on purpose: they come from the
specification, not from the code under test.
"""

import contextlib
import logging
import os
import unittest
from unittest import mock

from click.testing import CliRunner
from flask import Flask
from flask_testing import TestCase

import cornflow.app as app_module
from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.commands.access import access_init_command
from cornflow.config import app_config
from cornflow.models import UserModel, UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import PLANNER_ROLE
from cornflow.shared.exceptions import ConfigurationError
from cornflow.shared.security_levels import (
    SECURITY_LEVEL_ENV_VAR,
    SETTINGS_BY_ENV_VAR,
    resolve_security_settings,
)
from cornflow.tests.const import HEALTH_URL, LOGIN_URL, TOKEN_URL
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    security_level_config,
)

LEVELS = (1, 2, 3)
PASSWORD = "Kx9#tR2m!Qw7Zp"
APP_LOGGER = "cornflow.app"
MFA_DEPENDENT = ("MFA_REQUIRED", "API_KEY_STEPUP_TOTP", "PLATFORM_ROLE_STEPUP_TOTP")


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
def capture_app_log():
    """
    Captures the records of the application logger. dictConfig is replaced by a
    no-op while the app is created, otherwise create_app would reset the
    handlers of the logger and drop the capture. Works also when create_app raises.
    """
    handler = _ListHandler()
    logger = logging.getLogger(APP_LOGGER)
    logger.addHandler(handler)
    try:
        with mock.patch("cornflow.app.dictConfig"):
            yield handler
    finally:
        logger.removeHandler(handler)


def start(name):
    """create_app(name) capturing the log; returns (app, handler)."""
    with capture_app_log() as handler:
        app = create_app(name)
    return app, handler


def level_config(level=1, environ=None, **overrides):
    """Config name whose app logs at INFO (outside the inventory)."""
    return security_level_config(
        level, environ, **{"LOG_LEVEL": logging.INFO, **overrides}
    )


class TestInvalidSecurityLevel(unittest.TestCase):
    def test_invalid_levels_do_not_start(self):
        for value in ("4", "0", "-1", "abc", "", "   ", "1.5"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigurationError) as ctx:
                    create_app(security_level_config(value))
                for text in (ctx.exception.error, str(ctx.exception)):
                    self.assertIn("CORNFLOW_SECURITY_LEVEL", text)
                    self.assertIn(repr(value), text)
                    self.assertIn("1, 2 or 3", text)

    def test_exact_message(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(security_level_config("4"))
        self.assertEqual(
            "CORNFLOW_SECURITY_LEVEL must be 1, 2 or 3 (got '4')",
            ctx.exception.error,
        )

    def test_level_with_spaces_starts(self):
        app = create_app(security_level_config(" 2 "))
        self.assertEqual(2, app.config["SECURITY_LEVEL"])

    def test_unset_level_starts_at_level_1(self):
        app = create_app(security_level_config(None))
        self.assertEqual(1, app.config["SECURITY_LEVEL"])

    def test_invalid_level_is_checked_before_disabling_zero(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(security_level_config("4", LOGIN_MAX_ATTEMPTS=0))
        self.assertIn("CORNFLOW_SECURITY_LEVEL", ctx.exception.error)
        self.assertNotIn("LOGIN_MAX_ATTEMPTS", ctx.exception.error)


class TestDisablingZeroAtStartup(unittest.TestCase):
    def test_lockout_zero_does_not_start_at_levels_2_and_3(self):
        for level in (2, 3):
            for value in (0, -1):
                with self.subTest(level=level, value=value):
                    name = security_level_config(level, LOGIN_MAX_ATTEMPTS=value)
                    with self.assertRaises(ConfigurationError) as ctx:
                        create_app(name)
                    message = ctx.exception.error
                    self.assertEqual(
                        app_config[name].SECURITY_CONFIG_ERRORS[0], message
                    )
                    self.assertIn("LOGIN_MAX_ATTEMPTS", message)
                    self.assertIn("between 1 and 10", message)
                    self.assertIn(f"security level {level} does not allow", message)

    def test_bi_token_zero_does_not_start_at_level_3(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(security_level_config(3, BI_TOKEN_DURATION_DAYS=0))
        self.assertIn("BI_TOKEN_DURATION_DAYS", ctx.exception.error)
        self.assertIn("between 1 and 365", ctx.exception.error)

    def test_two_zeros_are_reported_together(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(
                security_level_config(
                    3, LOGIN_MAX_ATTEMPTS=0, BI_TOKEN_DURATION_DAYS=0
                )
            )
        message = ctx.exception.error
        self.assertIn("LOGIN_MAX_ATTEMPTS", message)
        self.assertIn("BI_TOKEN_DURATION_DAYS", message)
        self.assertLess(
            message.index("LOGIN_MAX_ATTEMPTS"), message.index("BI_TOKEN_DURATION_DAYS")
        )
        self.assertIn("; ", message)
        self.assertEqual(2, len(message.split("; ")))

    def test_zero_is_allowed_where_the_level_admits_it(self):
        cases = (
            (1, "LOGIN_MAX_ATTEMPTS"),
            (1, "BI_TOKEN_DURATION_DAYS"),
            (2, "BI_TOKEN_DURATION_DAYS"),
        )
        for level, name in cases:
            with self.subTest(level=level, name=name):
                app = create_app(security_level_config(level, **{name: 0}))
                self.assertEqual(0, app.config[name])

    def test_disabling_zero_is_checked_before_mfa_coherence(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(security_level_config(2, LOGIN_MAX_ATTEMPTS=0, MFA_REQUIRED=1))
        self.assertIn("LOGIN_MAX_ATTEMPTS", ctx.exception.error)
        self.assertNotIn("MFA_ENABLED", ctx.exception.error)

    def test_other_out_of_bounds_values_start(self):
        app, handler = start(level_config(2, LOGIN_MAX_ATTEMPTS=20))
        self.assertEqual(10, app.config["LOGIN_MAX_ATTEMPTS"])
        warnings = handler.lines(logging.WARNING)
        self.assertTrue(
            any("requested '20', applied 10" in line for line in warnings), warnings
        )


class TestMfaEnabledCoherence(unittest.TestCase):
    def test_defaults_of_every_level_start(self):
        for level in LEVELS:
            with self.subTest(level=level):
                create_app(security_level_config(level))

    def test_testing_config_starts(self):
        create_app("testing")

    def test_mfa_dependent_setting_without_mfa_enabled(self):
        for level in (1, 2):
            for var in MFA_DEPENDENT:
                with self.subTest(level=level, var=var):
                    with self.assertRaises(ConfigurationError) as ctx:
                        create_app(security_level_config(level, **{var: 1}))
                    self.assertEqual(
                        f"{var}=1 needs MFA_ENABLED=1, but MFA_ENABLED is 0: "
                        f"set MFA_ENABLED=1, or set {var} to 0",
                        ctx.exception.error,
                    )

    def test_mfa_dependent_setting_with_mfa_enabled(self):
        app = create_app(security_level_config(1, MFA_REQUIRED=1, MFA_ENABLED=1))
        self.assertEqual(1, app.config["MFA_ENABLED"])
        self.assertEqual(1, app.config["MFA_REQUIRED"])

    def test_level_3_without_mfa_enabled_names_the_three(self):
        with self.assertRaises(ConfigurationError) as ctx:
            create_app(security_level_config(3, MFA_ENABLED=0))
        self.assertEqual(
            "MFA_REQUIRED=1, API_KEY_STEPUP_TOTP=1, PLATFORM_ROLE_STEPUP_TOTP=1 "
            "need MFA_ENABLED=1, but MFA_ENABLED is 0: set MFA_ENABLED=1, or set "
            "MFA_REQUIRED, API_KEY_STEPUP_TOTP, PLATFORM_ROLE_STEPUP_TOTP to 0",
            ctx.exception.error,
        )

    def test_level_3_without_mfa_at_all_starts(self):
        app = create_app(
            security_level_config(
                3,
                MFA_ENABLED=0,
                MFA_REQUIRED=0,
                API_KEY_STEPUP_TOTP=0,
                PLATFORM_ROLE_STEPUP_TOTP=0,
            )
        )
        self.assertEqual(0, app.config["MFA_ENABLED"])

    def test_check_function_directly(self):
        flask_app = Flask(__name__)
        flask_app.config.update(
            MFA_ENABLED=0,
            MFA_REQUIRED=1,
            API_KEY_STEPUP_TOTP=0,
            PLATFORM_ROLE_STEPUP_TOTP=1,
        )
        with self.assertRaises(ConfigurationError) as ctx:
            app_module._check_mfa_coherence(flask_app)
        message = ctx.exception.error
        self.assertIn("MFA_REQUIRED=1, PLATFORM_ROLE_STEPUP_TOTP=1 need", message)
        self.assertNotIn("API_KEY_STEPUP_TOTP", message)

    def test_check_function_passes_when_mfa_enabled(self):
        flask_app = Flask(__name__)
        flask_app.config.update(MFA_ENABLED=1, MFA_REQUIRED=1)
        app_module._check_mfa_coherence(flask_app)


class TestSecurityLevelLog(unittest.TestCase):
    def test_level_line_without_changes(self):
        for level in LEVELS:
            with self.subTest(level=level):
                _, handler = start(level_config(level))
                lines = handler.lines(logging.INFO)
                self.assertEqual(
                    1,
                    len([line for line in lines if line.startswith("Security level:")]),
                    lines,
                )
                self.assertIn(f"Security level: {level}", lines)
                for line in handler.lines():
                    self.assertNotIn("changed setting", line)
                    self.assertNotIn("adjusted setting", line)

    def test_changed_setting_is_logged(self):
        _, handler = start(level_config(2, TOKEN_DURATION=12))
        self.assertIn(
            "Security level 2, changed setting: TOKEN_DURATION: "
            "level default 8.0, effective 12.0",
            handler.lines(logging.INFO),
        )

    def test_adjusted_setting_is_a_warning(self):
        for level in (2, 3):
            with self.subTest(level=level):
                _, handler = start(level_config(level, TOKEN_DURATION=30))
                self.assertIn(
                    f"Security level {level}, adjusted setting: TOKEN_DURATION: "
                    f"requested '30', applied 24.0 (maximum allowed at security "
                    f"level {level})",
                    handler.lines(logging.WARNING),
                )

    def test_level_1_has_no_limit_so_no_warning(self):
        _, handler = start(level_config(1, TOKEN_DURATION=30))
        self.assertEqual([], [x for x in handler.lines(logging.WARNING) if "TOKEN_DURATION" in x])
        self.assertIn(
            "Security level 1, changed setting: TOKEN_DURATION: "
            "level default 24.0, effective 30.0",
            handler.lines(logging.INFO),
        )

    def test_unparseable_value_is_a_warning(self):
        _, handler = start(level_config(2, environ={"LOGIN_MAX_ATTEMPTS": "abc"}))
        warnings = handler.lines(logging.WARNING)
        self.assertTrue(
            any(
                "LOGIN_MAX_ATTEMPTS" in line
                and "requested 'abc' is not a valid int" in line
                for line in warnings
            ),
            warnings,
        )

    def test_keys_are_never_logged(self):
        token_key = "T" * 44
        bi_key = "B" * 44
        _, handler = start(
            level_config(
                2,
                SECRET_TOKEN_KEY=token_key,
                SECRET_BI_KEY=bi_key,
                RATELIMIT_STORAGE_URI="redis://:s3cr3tpwd@host:6379/0",
            )
        )
        text = "\n".join(handler.lines())
        self.assertNotIn(token_key, text)
        self.assertNotIn(bi_key, text)
        self.assertNotIn("s3cr3tpwd", text)
        self.assertIn("value set (hidden)", text)

    def test_nothing_logged_when_startup_fails(self):
        with capture_app_log() as handler:
            with self.assertRaises(ConfigurationError):
                create_app(level_config("abc"))
        for line in handler.lines():
            self.assertNotIn("Security level:", line)


class _NotExposedBase(SecurityLevelTestMixin, TestCase):
    __test__ = False

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

    def test_level_is_not_in_any_response(self):
        login = self.client.post(
            LOGIN_URL, json={"username": "smokeuser", "password": PASSWORD}
        )
        self.assertEqual(200, login.status_code, login.json)
        token = login.json["token"]
        responses = {
            "health": self.client.get(HEALTH_URL),
            "login": login,
            "token": self.client.get(
                TOKEN_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            ),
        }
        for name, response in responses.items():
            text = response.get_data(as_text=True) + str(response.headers)
            for forbidden in ("SECURITY_LEVEL", "SECURITY_", "MFA_ENABLED"):
                with self.subTest(response=name, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)
            with self.subTest(response=name, forbidden="security_level"):
                self.assertNotIn("security_level", text.lower())


class TestSecurityLevelNotExposedLevel1(_NotExposedBase):
    __test__ = True
    security_level = 1


class TestSecurityLevelNotExposedLevel2(_NotExposedBase):
    __test__ = True
    security_level = 2


class TestSecurityLevelNotExposedLevel3(_NotExposedBase):
    __test__ = True
    security_level = 3
    config_overrides = {"MFA_REQUIRED": 0}


class TestSessionWindowsByLevel(unittest.TestCase):
    def test_no_warning_with_level_defaults(self):
        for level in LEVELS:
            with self.subTest(level=level):
                _, handler = start(level_config(level))
                for line in handler.lines():
                    self.assertFalse(line.startswith("REFRESH_TOKEN_"), line)

    def test_incoherent_windows_only_warn_with_refresh(self):
        windows = {
            "REFRESH_TOKEN_INACTIVITY_MINUTES": 600,
            "REFRESH_TOKEN_ABSOLUTE_HOURS": 2,
        }
        for level in (1, 2):
            with self.subTest(level=level):
                _, handler = start(level_config(level, **windows))
                for line in handler.lines():
                    self.assertFalse(line.startswith("REFRESH_TOKEN_"), line)
        _, handler = start(level_config(3, MFA_REQUIRED=0, **windows))
        self.assertTrue(
            any(
                line.startswith("REFRESH_TOKEN_ABSOLUTE_HOURS (2h) is not longer than")
                for line in handler.lines(logging.WARNING)
            ),
            handler.lines(),
        )


def _fake_initialize_database(app, external_app_module=None):
    """Replaces the Alembic migrations, which do not run on SQLite."""
    with app.app_context():
        db.create_all()
        access_init_command(verbose=False)


class TestServiceInitSecurity(TestCase):
    ADMIN_PWD = "Granito-Vela-Oruga7"
    SERVICE_PWD = "Mimbre-Faro-Ciervo4"

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def run_init(self, level, extra_env=None, environ=None, **overrides):
        """
        Runs `cornflow service init` with the configuration of the given level.
        Returns (result, os.system mock, os.environ snapshot taken inside the patch).
        """
        name = security_level_config(level, environ, **overrides)
        env = {
            "FLASK_ENV": name,
            "CORNFLOW_BACKEND": "1",
            "AUTH_TYPE": "1",
            "CORNFLOW_ADMIN_PWD": self.ADMIN_PWD,
            "CORNFLOW_SERVICE_PWD": self.SERVICE_PWD,
        }
        env.update(extra_env or {})
        uri = app_config[name].SQLALCHEMY_DATABASE_URI
        with mock.patch.dict(os.environ, env):
            if "SIGNUP_ACTIVATED" not in (extra_env or {}):
                os.environ.pop("SIGNUP_ACTIVATED", None)
            with mock.patch("cornflow.cli.service.os.chdir"), mock.patch(
                "cornflow.cli.service.get_db_conn", return_value=uri
            ), mock.patch("cornflow.cli.service._sync_with_airflow"), mock.patch(
                "cornflow.cli.service._initialize_database",
                side_effect=_fake_initialize_database,
            ), mock.patch(
                "cornflow.cli.service.os.system"
            ) as system:
                result = CliRunner().invoke(cli, ["service", "init"])
                snapshot = dict(os.environ)
        return result, system, snapshot

    @staticmethod
    def gunicorn_started(system):
        return any("gunicorn" in str(call.args[0]) for call in system.call_args_list)

    def assert_init_stopped(self, level, message, **kwargs):
        with self.assertLogs("cornflow.service", "ERROR") as logs:
            result, system, _ = self.run_init(level, **kwargs)
        self.assertNotEqual(0, result.exit_code)
        self.assertIn(message, result.output)
        self.assertTrue(
            any("Cornflow can not start:" in line for line in logs.output), logs.output
        )
        self.assertEqual(0, UserModel.query.count())
        self.assertFalse(self.gunicorn_started(system))

    def test_invalid_level_stops_init(self):
        self.assert_init_stopped("abc", "CORNFLOW_SECURITY_LEVEL must be 1, 2 or 3")

    def test_disabling_zero_stops_init(self):
        self.assert_init_stopped(
            2, "LOGIN_MAX_ATTEMPTS=0", LOGIN_MAX_ATTEMPTS=0
        )
        self.assert_init_stopped(
            3, "BI_TOKEN_DURATION_DAYS=0", MFA_REQUIRED=0, BI_TOKEN_DURATION_DAYS=0
        )

    def test_disabling_zero_allowed_starts_init(self):
        result, system, _ = self.run_init(1, LOGIN_MAX_ATTEMPTS=0)
        self.assertEqual(0, result.exit_code, result.output)
        for username in ("cornflow_admin", "service_user"):
            self.assertIsNotNone(UserModel.get_one_user_by_username(username))
        self.assertTrue(self.gunicorn_started(system))

    def test_mfa_incoherence_stops_init(self):
        self.assert_init_stopped(1, "MFA_REQUIRED=1 needs MFA_ENABLED=1", MFA_REQUIRED=1)

    def test_signup_activated_is_not_set(self):
        result, system, snapshot = self.run_init(1)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("SIGNUP_ACTIVATED", snapshot)
        expected = {1: 2, 2: 3, 3: 3}
        for level in LEVELS:
            with self.subTest(level=level):
                env = dict(snapshot, **{SECURITY_LEVEL_ENV_VAR: str(level)})
                resolved = resolve_security_settings(env)
                self.assertEqual(expected[level], resolved.values["SIGNUP_ACTIVATED"])

    def test_operator_signup_activated_is_kept(self):
        result, system, snapshot = self.run_init(1, extra_env={"SIGNUP_ACTIVATED": "1"})
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("1", snapshot["SIGNUP_ACTIVATED"])
        for level in LEVELS:
            with self.subTest(level=level):
                env = dict(snapshot, **{SECURITY_LEVEL_ENV_VAR: str(level)})
                self.assertEqual(
                    1, resolve_security_settings(env).values["SIGNUP_ACTIVATED"]
                )


class TestServiceInitEnvironment(unittest.TestCase):
    BASE = {"PATH": os.environ.get("PATH", ""), "CORNFLOW_BACKEND": "1"}

    def setup_environment(self, extra=None):
        from cornflow.cli.service import _setup_environment_variables

        with mock.patch.dict(os.environ, {**self.BASE, **(extra or {})}, clear=True):
            before = dict(os.environ)
            with mock.patch(
                "cornflow.cli.service.get_db_conn", return_value="sqlite://"
            ):
                config = _setup_environment_variables()
            after = dict(os.environ)
        changed = {k for k, v in after.items() if before.get(k) != v}
        return config, changed

    def test_init_does_not_write_inventory_variables(self):
        _, changed = self.setup_environment()
        self.assertEqual(set(), changed & set(SETTINGS_BY_ENV_VAR))
        self.assertNotIn(SECURITY_LEVEL_ENV_VAR, changed)
        self.assertNotIn("SIGNUP_ACTIVATED", changed)

    def test_default_passwords_are_the_1_3_9_ones(self):
        config, _ = self.setup_environment()
        self.assertEqual("Cornflow_admin1234", config["cornflow_admin_pwd"])
        self.assertEqual("Service_user1234", config["cornflow_service_pwd"])

    def test_environment_passwords_win(self):
        config, _ = self.setup_environment(
            {"CORNFLOW_ADMIN_PWD": "A-pwd-1", "CORNFLOW_SERVICE_PWD": "S-pwd-2"}
        )
        self.assertEqual("A-pwd-1", config["cornflow_admin_pwd"])
        self.assertEqual("S-pwd-2", config["cornflow_service_pwd"])

    def test_airflow_script_default_service_password(self):
        import cornflow

        path = os.path.join(
            os.path.dirname(cornflow.__file__),
            "..",
            "airflow_config",
            "scripts",
            "init_airflow_service.py",
        )
        # Read as text: importing the script executes it
        with open(path, encoding="utf-8") as script:
            content = script.read()
        self.assertIn('("CORNFLOW_SERVICE_PWD", "Service_user1234")', content)
        self.assertNotIn("Mimbre-Faro-Ciervo4", content)


if __name__ == "__main__":
    unittest.main()
