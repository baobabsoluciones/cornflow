"""
Checks of the server UAT battery itself (task016): the security level selector,
the helpers by level, the configuration derived from the inventory of
``cornflow.shared.security_levels`` and the number of cases and skips at each
level.

The module name does not match ``test_uat_hardening_*.py`` on purpose: the
battery is run by level with that pattern, and these checks do not depend on
the level of the process that runs them. Everything that depends on the
level (import of the support module, collection of the cases) runs in a
subprocess with its own ``CORNFLOW_SECURITY_LEVEL``.

The skips are read from the decorators (``__unittest_skip__``) without running
the cases. The pass of the battery at each level is checked by running it (see
tasks/task016/tests_preparados.md).
"""

import json
import os
import re
import subprocess
import sys
import unittest

SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
)
CORNFLOW_DIR = os.path.join(SERVER_DIR, "cornflow")
THIS_FILE = os.path.abspath(__file__)
SUPPORT_FILE = os.path.join(CORNFLOW_DIR, "tests", "uat_hardening_support.py")

LEVEL_VAR = "CORNFLOW_SECURITY_LEVEL"
# Built from pieces so that this file does not match its own search
OLD_PROFILE_VAR = "CORNFLOW_UAT_" + "PROFILE"

BATTERY_MODULES = (
    "cornflow.tests.unit.test_uat_hardening_auth",
    "cornflow.tests.unit.test_uat_hardening_sessions",
    "cornflow.tests.unit.test_uat_hardening_keys_audit",
)

TOTAL_CASES = 134
NEW_CASES = (
    "test_uat_11_3_hsts_level_default",
    "test_uat_11_4_cors_level_default",
    "test_uat_11_6_docs_level_default",
)
UI_ONLY_IDS = {"3_5", "6_13", "6_15", "11_8", "12_7"}
RENEWAL_IDS = {
    "6_3", "6_4", "6_5", "6_7", "6_8", "6_9", "6_14", "6_16", "10_10", "10_11", "12_5",
}
EXPECTED_SKIPPED = {1: 16, 2: 16, 3: 5}

REMOVED_NAMES = (
    "STRICT", "RELAXED", "PROFILE", "PROFILES", "SETTINGS",
    "is_strict", "is_relaxed", "profile_env_name", "pending_fix",
)
REQUIRED_NAMES = (
    "LEVEL", "LEVEL_DEFAULTS", "read_security_level", "level", "at_least",
    "by_level", "level_overrides", "only_at_levels", "requires_token_renewal",
    "MFA_ENROLLMENT_OVERRIDES", "LOCKOUT_OVERRIDES", "ROTATION_OVERRIDES",
    "SIGNUP_ADMIN", "uat_env_name", "ui_only", "UatTestCase", "FakeSMTP",
)

# Settings a case may change on purpose in the support module (the rest comes
# from the inventory of the level)
ALLOWED_HAND_SET_KEYS = {"MFA_ENABLED", "LOGIN_MAX_ATTEMPTS", "PWD_ROTATION_ENFORCE"}


def child_env(level=None, **extra):
    env = {
        k: v for k, v in os.environ.items() if k not in (LEVEL_VAR, OLD_PROFILE_VAR)
    }
    env.setdefault("FLASK_ENV", "testing")
    env.setdefault("OPEN_DEPLOYMENT", "1")
    env.setdefault("LOG_LEVEL", "30")
    if level is not None:
        env[LEVEL_VAR] = level
    env.update(extra)
    return env


def run_python(code, level=None, **extra):
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=SERVER_DIR,
        env=child_env(level, **extra),
        capture_output=True,
        text=True,
        timeout=300,
    )


def last_json(result):
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


IMPORT_SUPPORT = "import cornflow.tests.uat_hardening_support as s; "


class SelectorTests(unittest.TestCase):
    """E2E-O03: selector of the battery."""

    def level_of(self, level=None, **extra):
        result = run_python(IMPORT_SUPPORT + "print(s.LEVEL)", level, **extra)
        self.assertEqual(0, result.returncode, result.stderr[-3000:])
        return int(result.stdout.strip().splitlines()[-1]), result.stderr

    def test_unset_is_level_1(self):
        level, stderr = self.level_of(None)
        self.assertEqual(1, level)
        self.assertIn("UAT hardening battery: security level 1", stderr)

    def test_valid_levels(self):
        for raw, expected in (("1", 1), ("2", 2), ("3", 3), (" 2 ", 2)):
            with self.subTest(raw=raw):
                level, stderr = self.level_of(raw)
                self.assertEqual(expected, level)
                self.assertIn(
                    f"UAT hardening battery: security level {expected}", stderr
                )

    def test_old_profile_variable_has_no_effect(self):
        for value in ("relaxed", "strict"):
            with self.subTest(profile=value):
                level, stderr = self.level_of(None, **{OLD_PROFILE_VAR: value})
                self.assertEqual(1, level)
                self.assertIn("security level 1", stderr)
        level, _ = self.level_of("3", **{OLD_PROFILE_VAR: "relaxed"})
        self.assertEqual(3, level)

    def test_invalid_value_stops_the_import_with_a_clear_error(self):
        for raw in ("4", "0", "abc", "relaxed", "strict", ""):
            with self.subTest(raw=raw):
                result = run_python(IMPORT_SUPPORT + "print(s.LEVEL)", raw)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("ValueError", result.stderr)
                self.assertIn(LEVEL_VAR, result.stderr)
                self.assertRegex(result.stderr, r"1, 2 or 3")

    def test_invalid_value_fails_the_three_modules_and_runs_no_case(self):
        for raw in ("4", "abc", "relaxed", "strict", ""):
            with self.subTest(raw=raw):
                result = subprocess.run(
                    [
                        sys.executable, "-m", "unittest", "discover", "-s",
                        "cornflow/tests/unit", "-p", "test_uat_hardening_*.py",
                    ],
                    cwd=SERVER_DIR,
                    env=child_env(raw),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(3, result.stderr.count("ImportError"), result.stderr[-3000:])
                self.assertIn(LEVEL_VAR, result.stderr)
                # Only the three failed imports are "run"; no case of the battery
                self.assertIn("Ran 3 tests", result.stderr)
                self.assertNotIn("test_uat_1_", result.stderr)

    def test_read_security_level_accepts_an_explicit_environment(self):
        code = IMPORT_SUPPORT + (
            "import json; "
            "ok = {k: s.read_security_level({'CORNFLOW_SECURITY_LEVEL': k}) for k in ('1','2','3')}; "
            "ok['unset'] = s.read_security_level({}); "
            "bad = []\n"
            "for k in ('4', 'abc', ''):\n"
            "    try:\n"
            "        s.read_security_level({'CORNFLOW_SECURITY_LEVEL': k})\n"
            "    except ValueError as e:\n"
            "        bad.append(str(e))\n"
            "print(json.dumps([ok, bad]))"
        )
        ok, bad = last_json(run_python(code, "1"))
        self.assertEqual({"1": 1, "2": 2, "3": 3, "unset": 1}, ok)
        self.assertEqual(3, len(bad))
        for message in bad:
            self.assertIn(LEVEL_VAR, message)


class RemovedProfileTests(unittest.TestCase):
    """The profile machinery is gone and the helpers by level replace it."""

    def test_removed_and_required_names(self):
        code = IMPORT_SUPPORT + (
            "import json; "
            f"print(json.dumps([[n for n in {REMOVED_NAMES!r} if hasattr(s, n)], "
            f"[n for n in {REQUIRED_NAMES!r} if not hasattr(s, n)]]))"
        )
        for level in ("1", "3"):
            with self.subTest(level=level):
                still_there, missing = last_json(run_python(code, level))
                self.assertEqual([], still_there)
                self.assertEqual([], missing)

    def test_helpers_by_level(self):
        code = IMPORT_SUPPORT + (
            "import json, unittest\n"
            "skipped = s.only_at_levels(2, reason='some reason')(lambda self: None)\n"
            "renewal = s.requires_token_renewal(lambda self: None)\n"
            "print(json.dumps({\n"
            "  'level': s.level(),\n"
            "  'at_least': [s.at_least(n) for n in (1, 2, 3)],\n"
            "  'by_level': s.by_level('a', 'b', 'c'),\n"
            "  'overrides': s.level_overrides({'X': 1}, None, {'Y': 2}),\n"
            "  'only_skip': getattr(skipped, '__unittest_skip__', False),\n"
            "  'only_why': getattr(skipped, '__unittest_skip_why__', ''),\n"
            "  'renewal_skip': getattr(renewal, '__unittest_skip__', False),\n"
            "  'renewal_why': getattr(renewal, '__unittest_skip_why__', ''),\n"
            "}))"
        )
        for level in (1, 2, 3):
            with self.subTest(level=level):
                got = last_json(run_python(code, str(level)))
                self.assertEqual(level, got["level"])
                self.assertEqual([level >= n for n in (1, 2, 3)], got["at_least"])
                self.assertEqual("abc"[level - 1], got["by_level"])
                self.assertEqual({1: {"X": 1}, 2: {}, 3: {"Y": 2}}[level], got["overrides"])
                self.assertEqual(level != 2, got["only_skip"])
                if level != 2:
                    self.assertIn(f"security level {level}", got["only_why"])
                    self.assertIn("some reason", got["only_why"])
                self.assertEqual(level != 3, got["renewal_skip"])
                if level != 3:
                    self.assertIn(f"security level {level}", got["renewal_why"])
                    self.assertIn("REFRESH_TOKEN_ENABLED=0", got["renewal_why"])

    def test_no_old_name_left_in_the_server_tree(self):
        """E2E-O04 (task016 part): grep of the old names in cornflow-server/cornflow."""
        pattern = re.compile(
            "|".join(
                (
                    OLD_PROFILE_VAR,
                    "is_" + "strict",
                    "is_" + "relaxed",
                    "RELAX" + "ED",
                    "relaxed" + " profile",
                    "strict" + " profile",
                    "pending" + "_fix",
                )
            )
        )
        # Exception (decision of the orchestrator): a task001 test that talks
        # about the strict production, not about the old profile.
        allowed = (
            "test_security_levels.py",
            "test_level_3_is_strict_with_any_flask_env",
        )
        found = []
        for root, dirs, files in os.walk(CORNFLOW_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                path = os.path.join(root, name)
                if os.path.abspath(path) == THIS_FILE or name.endswith((".pyc", ".db", ".db-journal")):
                    continue
                try:
                    with open(path, encoding="utf-8") as handle:
                        lines = handle.readlines()
                except (UnicodeDecodeError, OSError):
                    continue
                for number, line in enumerate(lines, 1):
                    if pattern.search(line):
                        if name == allowed[0] and allowed[1] in line:
                            continue
                        found.append(f"{os.path.relpath(path, SERVER_DIR)}:{number}: {line.strip()}")
        self.assertEqual([], found)


class SupportModuleSourceTests(unittest.TestCase):
    """Criteria 2 and 6: nothing repeated by hand, docstring with the commands."""

    @classmethod
    def setUpClass(cls):
        with open(SUPPORT_FILE, encoding="utf-8") as handle:
            cls.source = handle.read()

    def test_docstring_explains_the_run_by_level(self):
        code = IMPORT_SUPPORT + "import json; print(json.dumps(s.__doc__))"
        doc = last_json(run_python(code, "1"))
        for n in (1, 2, 3):
            self.assertIn(
                f'CORNFLOW_SECURITY_LEVEL={n} python -m unittest discover '
                '-s cornflow/tests/unit -p "test_uat_hardening_*.py"',
                doc,
            )
        self.assertIn("level 1 when the variable is unset", doc.replace("\n", " ").replace("  ", " "))
        self.assertNotIn(OLD_PROFILE_VAR, doc)

    def test_config_comes_from_the_security_level_helper(self):
        self.assertIn("security_level_config", self.source)
        self.assertIn("default_values", self.source)
        self.assertIn("parse_security_level", self.source)

    def test_inventory_values_are_not_repeated_by_hand(self):
        code = (
            "import json; from cornflow.shared.security_levels import SETTINGS_BY_CONFIG_KEY; "
            "print(json.dumps(sorted(SETTINGS_BY_CONFIG_KEY)))"
        )
        keys = last_json(run_python(code, "1"))
        # Reads of the app configuration (``config["KEY"]``) are not values set by hand
        written = re.sub(r"""config\[\s*["'][A-Z0-9_]+["']\s*\]""", "config[...]", self.source)
        quoted = {k for k in keys if re.search(r"""["']%s["']""" % re.escape(k), written)}
        self.assertLessEqual(quoted, ALLOWED_HAND_SET_KEYS, sorted(quoted - ALLOWED_HAND_SET_KEYS))


class LevelConfigTests(unittest.TestCase):
    """The configuration of the battery is the inventory of the level."""

    CODE = IMPORT_SUPPORT + (
        "import json\n"
        "from cornflow.config import app_config\n"
        "from cornflow.shared.security_levels import default_values\n"
        "cls = app_config[s.uat_env_name()]\n"
        "defaults = default_values(s.LEVEL)\n"
        "diff = {k: [getattr(cls, k, None), v] for k, v in defaults.items()\n"
        "        if k not in ('RATELIMIT_ENABLED', 'BCRYPT_LOG_ROUNDS') and getattr(cls, k, None) != v}\n"
        "locked = app_config[s.uat_env_name(LOGIN_MAX_ATTEMPTS=3)]\n"
        "short = app_config[s.uat_env_name(PWD_MIN_LENGTH=6)]\n"
        "print(json.dumps({\n"
        "  'diff': diff,\n"
        "  'ratelimit': cls.RATELIMIT_ENABLED,\n"
        "  'bcrypt': cls.BCRYPT_LOG_ROUNDS,\n"
        "  'level': cls.SECURITY_LEVEL,\n"
        "  'same_name': s.uat_env_name() == s.uat_env_name(),\n"
        "  'login_max_3': locked.LOGIN_MAX_ATTEMPTS,\n"
        "  'rate_on': app_config[s.uat_env_name(RATELIMIT_ENABLED=1)].RATELIMIT_ENABLED,\n"
        "  'pwd_min_6': short.PWD_MIN_LENGTH,\n"
        "  'pwd_min_default': defaults['PWD_MIN_LENGTH'],\n"
        "}))"
    )

    def test_configuration_equals_the_defaults_of_the_level(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                got = last_json(run_python(self.CODE, str(level)))
                self.assertEqual({}, got["diff"])
                self.assertEqual(level, got["level"])
                self.assertEqual(0, got["ratelimit"])
                self.assertEqual(4, got["bcrypt"])
                self.assertTrue(got["same_name"])
                self.assertEqual(1, got["rate_on"])
                # A change on purpose goes through the resolution of the level
                self.assertEqual(3, got["login_max_3"])
                if level == 1:
                    self.assertEqual(6, got["pwd_min_6"])
                else:
                    self.assertEqual(got["pwd_min_default"], got["pwd_min_6"])

    def test_values_of_table_4_2_for_key_settings(self):
        code = IMPORT_SUPPORT + (
            "import json; d = s.LEVEL_DEFAULTS; "
            "print(json.dumps({k: d[k] for k in ('HSTS_ENABLED', 'CORS_ORIGINS', 'DOCS_ENABLED', "
            "'MFA_REQUIRED', 'LOGIN_MAX_ATTEMPTS', 'REFRESH_TOKEN_ENABLED', 'SIGNUP_ACTIVATED')}))"
        )
        expected = {
            1: dict(HSTS_ENABLED=0, CORS_ORIGINS="*", DOCS_ENABLED=1, MFA_REQUIRED=0,
                    LOGIN_MAX_ATTEMPTS=0, REFRESH_TOKEN_ENABLED=0, SIGNUP_ACTIVATED=2),
            2: dict(HSTS_ENABLED=0, CORS_ORIGINS="*", DOCS_ENABLED=1, MFA_REQUIRED=0,
                    LOGIN_MAX_ATTEMPTS=5, REFRESH_TOKEN_ENABLED=0, SIGNUP_ACTIVATED=3),
            3: dict(HSTS_ENABLED=1, CORS_ORIGINS="", DOCS_ENABLED=0, MFA_REQUIRED=1,
                    LOGIN_MAX_ATTEMPTS=5, REFRESH_TOKEN_ENABLED=1, SIGNUP_ACTIVATED=3),
        }
        for level, values in expected.items():
            with self.subTest(level=level):
                got = last_json(run_python(code, str(level)))
                self.assertEqual(values, {k: (int(v) if isinstance(v, bool) else v) for k, v in got.items()})


COLLECT = (
    "import json, re, unittest\n"
    "loader = unittest.TestLoader()\n"
    "rows = []\n"
    f"for name in {BATTERY_MODULES!r}:\n"
    "    suite = loader.loadTestsFromName(name)\n"
    "    stack = [suite]\n"
    "    while stack:\n"
    "        item = stack.pop()\n"
    "        if isinstance(item, unittest.TestSuite):\n"
    "            stack.extend(item)\n"
    "            continue\n"
    "        method = getattr(type(item), item._testMethodName, None)\n"
    "        cls = type(item)\n"
    "        skip = bool(getattr(method, '__unittest_skip__', False) or getattr(cls, '__unittest_skip__', False))\n"
    "        why = getattr(method, '__unittest_skip_why__', '') or getattr(cls, '__unittest_skip_why__', '')\n"
    "        xfail = bool(getattr(method, '__unittest_expecting_failure__', False) or getattr(cls, '__unittest_expecting_failure__', False))\n"
    "        rows.append([name.rsplit('.', 1)[1], cls.__name__, item._testMethodName, skip, why, xfail])\n"
    "print(json.dumps(rows))\n"
)


class CollectionTests(unittest.TestCase):
    """E2E-O02 (counts) and criterion 7: cases and skips by level, without running them."""

    rows = {}

    @classmethod
    def collected(cls, level):
        if level not in cls.rows:
            cls.rows[level] = last_json(run_python(COLLECT, str(level)))
        return cls.rows[level]

    @staticmethod
    def case_id(method):
        found = re.match(r"test_uat_(\d+_\d+)_", method)
        return found.group(1) if found else None

    def test_total_number_of_cases_is_134_at_every_level(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                rows = self.collected(level)
                self.assertEqual(TOTAL_CASES, len(rows))
                methods = [r[2] for r in rows]
                self.assertEqual(len(methods), len(set(zip(methods, [r[1] for r in rows]))))
                for new in NEW_CASES:
                    self.assertIn(new, methods)
                self.assertTrue(all(m.startswith("test_uat_") for m in methods))

    def test_same_cases_at_every_level(self):
        names = {level: sorted((r[0], r[1], r[2]) for r in self.collected(level)) for level in (1, 2, 3)}
        self.assertEqual(names[1], names[2])
        self.assertEqual(names[1], names[3])

    def test_skipped_count_by_level(self):
        for level, expected in EXPECTED_SKIPPED.items():
            with self.subTest(level=level):
                skipped = [r for r in self.collected(level) if r[3]]
                self.assertEqual(expected, len(skipped), sorted(r[2] for r in skipped))

    def test_skipped_cases_by_level(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                skipped = {self.case_id(r[2]): r[4] for r in self.collected(level) if r[3]}
                expected = set(UI_ONLY_IDS) | (set() if level == 3 else set(RENEWAL_IDS))
                self.assertEqual(expected, set(skipped))
                for case in UI_ONLY_IDS:
                    self.assertTrue(skipped[case].startswith("cornflow-ui"), skipped[case])
                if level != 3:
                    for case in RENEWAL_IDS:
                        self.assertIn(f"security level {level}:", skipped[case])
                        self.assertIn("token renewal", skipped[case])

    def test_every_skip_has_a_reason_that_names_the_level_or_the_ui(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                for _, _, method, skip, why, _ in self.collected(level):
                    if skip:
                        self.assertTrue(
                            why.startswith("cornflow-ui") or why.startswith(f"security level {level}"),
                            f"{method}: {why!r}",
                        )

    def test_no_expected_failure(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                self.assertEqual([], [r[2] for r in self.collected(level) if r[5]])

    def test_lockout_mfa_and_rotation_cases_are_not_skipped(self):
        running = {"4_2", "4_3", "4_4", "4_5", "8_14", "10_4", "10_5",
                   "2_2", "2_3", "2_5", "2_6", "2_7", "2_8", "8_1", "8_2", "8_9", "10_7", "3_6"}
        for level in (1, 2, 3):
            with self.subTest(level=level):
                skipped = {self.case_id(r[2]) for r in self.collected(level) if r[3]}
                self.assertEqual(set(), running & skipped)


if __name__ == "__main__":
    unittest.main()
