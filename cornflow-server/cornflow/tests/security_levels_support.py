"""
Helpers to build test configurations for a given security level.

Kept outside tests/unit so that unittest discovery does not collect it.
"""

import json

from cornflow.app import create_app
from cornflow.config import Testing, app_config
from cornflow.shared.security_levels import (
    METADATA_CONFIG_KEYS,
    SECURITY_LEVEL_ENV_VAR,
    SETTINGS_BY_CONFIG_KEY,
    apply_security_settings,
    resolve_security_settings,
)

# Values the helper applies outside the inventory resolution, only to keep the
# tests fast and not throttled. They are not security levels.
TEST_FIXTURES = {"BCRYPT_LOG_ROUNDS": 4}


def _to_env_string(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def build_security_level_config(
    level=1, environ=None, key_environ=None, **overrides
) -> type:
    """
    Builds a Testing subclass with the values of the given security level.

    :param level: 1, 2, 3, or any raw value (str) to exercise an invalid level;
                  None leaves CORNFLOW_SECURITY_LEVEL unset.
    :param environ: raw environment strings (env var name -> str) passed as is to
                    the resolution, e.g. {"LOGIN_MAX_ATTEMPTS": "abc"}.
    :param key_environ: None keeps the fixed keys of Testing. A mapping (also
                        an empty one) resolves the secret keys from it as
                        config.py does with os.environ: FERNET_KEY, SECRET_KEY,
                        SECRET_BI_KEY and CORNFLOW_EPHEMERAL_SECRET_KEY.
                        Explicit SECRET_TOKEN_KEY / SECRET_BI_KEY overrides win.
    :param overrides: app.config keys. Inventory keys are converted to their
                      environment variable and go through the same resolution as
                      the environment. Any other key is set on the class as is.
    """
    environ = dict(environ or {})
    metadata = [key for key in overrides if key in METADATA_CONFIG_KEYS]
    if metadata:
        raise ValueError(
            f"{metadata} can not be overridden: choose the level with 'level'"
        )

    env = {}
    if level is not None:
        env[SECURITY_LEVEL_ENV_VAR] = str(level)

    attrs = {}
    override_env_vars = set()
    for key, value in overrides.items():
        setting = SETTINGS_BY_CONFIG_KEY.get(key)
        if setting is None:
            attrs[key] = value
            continue
        override_env_vars.add(setting.env_var)
        if value is not None:
            env[setting.env_var] = _to_env_string(value)

    conflicts = sorted(override_env_vars & set(environ))
    if conflicts:
        raise ValueError(f"{conflicts} given both in overrides and in environ")
    env.update(environ)

    attrs.update(TEST_FIXTURES)
    if "RATELIMIT_ENABLED" not in override_env_vars | set(environ):
        attrs["RATELIMIT_ENABLED"] = 0

    cls = type("SecurityLevelTestingConfig", (Testing,), attrs)
    resolved = resolve_security_settings(env)
    cls = apply_security_settings(cls, resolved)
    if key_environ is not None:
        # Imported here so that the other tests of the suite do not depend on it
        from cornflow.shared import secret_keys

        cls = secret_keys.apply_secret_keys(
            cls, secret_keys.resolve_secret_keys(dict(key_environ), resolved.level)
        )
    return cls


def security_level_config(
    level=1, environ=None, key_environ=None, **overrides
) -> str:
    """
    Registers (once) build_security_level_config(...) in app_config and returns
    its name, ready for create_app(name).
    """
    name = "testing-level-" + json.dumps(
        {
            "level": level,
            "environ": environ or {},
            "key_environ": key_environ,
            "overrides": overrides,
        },
        sort_keys=True,
        default=str,
    )
    if name not in app_config:
        app_config[name] = build_security_level_config(
            level, environ, key_environ, **overrides
        )
    return name


class SecurityLevelTestMixin:
    """
    Mixin for flask_testing based test cases: class SomeTest(SecurityLevelTestMixin, TestCase).
    """

    security_level = 1
    security_environ = {}
    key_environ = None
    config_overrides = {}

    def create_app(self):
        return create_app(
            security_level_config(
                self.security_level,
                self.security_environ,
                self.key_environ,
                **self.config_overrides,
            )
        )
