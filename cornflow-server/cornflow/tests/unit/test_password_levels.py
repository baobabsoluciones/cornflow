"""
Tests of the password rules that depend on the security level (task005):

- level 1 keeps the 1.3.9 pattern rules, levels 2 and 3 the full policy;
- history is stored at every level, reuse is only rejected from level 2;
- ``current_password`` and the similarity check only apply from level 2;
- passwords from the environment are validated with the rules of the level
  when the user is created (``cornflow users create`` and ``service init``);
- without an application context the strictest rules apply.

The expected messages are written in this file on purpose: they come from the
specification, not from the code under test.
"""

import json
import os
import random
import string
import unittest
from unittest import mock

from click.testing import CliRunner
from flask_testing import TestCase

from cornflow.app import create_app
from cornflow.cli import cli
from cornflow.commands.access import access_init_command
from cornflow.commands.users import create_user_with_role
from cornflow.models import UserModel, UserPasswordHistoryModel, UserRoleModel
from cornflow.shared import bcrypt, db
from cornflow.shared.const import ADMIN_ROLE, PASSWORD_SPECIAL_CHARACTERS, VIEWER_ROLE
from cornflow.shared.exceptions import InvalidCredentials
from cornflow.shared import validators
from cornflow.shared.validators import check_password_pattern
from cornflow.tests.const import LOGIN_URL, SIGNUP_URL, USER_URL
from cornflow.tests.security_levels_support import (
    SecurityLevelTestMixin,
    security_level_config,
)
from cornflow.tests.unit import test_security_startup as startup

P1 = "Kx9#tR2m!Qw7Zp"
P2 = "Hd6$vNc4&Ye2Bs"
P3 = "Mv4#qL8n!Zr5Tw"
GRANITO = "Granito-Vela-Oruga7"
# Shares half of P1 (similarity ratio 0.64): below the default threshold (0.8)
# and above 0.5
HALF_P1 = "Kx9#tR2m!Ab1Cd"
# Differs from P1 in one character only
CLOSE_P1 = "Kx9#tR2m!Qw7Zq"
JSON_HEADER = {"Content-Type": "application/json"}
INVALID_PWD_MESSAGE = "Password must"


def _check_password_pattern_1_3_9(password):
    """Literal copy of the password check of cornflow 1.3.9."""
    special = [char for char in "!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\"]
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
    if len(list(filter(lambda char: char in special, password))) == 0:
        return (
            False,
            "Password must contain at least one number and one special character.",
        )
    return True, None


def password_policy_enforced():
    """
    Reached through the module so that this file can be imported before the
    function exists: only the cases that use it fail until then.
    """
    return validators.password_policy_enforced()


def _overrides(**kwargs):
    return dict(kwargs)


class _PatternAssertions:
    def assert_rejected(self, password, message, user_data=None, exact=False):
        valid, msg = check_password_pattern(password, user_data=user_data)
        self.assertFalse(valid, f"{password!r} should be rejected")
        if exact:
            self.assertEqual(message, msg, password)
        else:
            self.assertIn(message, msg, password)

    def assert_accepted(self, password, user_data=None):
        valid, msg = check_password_pattern(password, user_data=user_data)
        self.assertTrue(valid, f"{password!r} should be accepted: {msg}")
        self.assertIsNone(msg)


# --------------------------------------------------------------------------
# A. Without application context
# --------------------------------------------------------------------------
class TestPasswordRulesWithoutAppContext(_PatternAssertions, unittest.TestCase):
    def test_policy_is_enforced(self):
        self.assertTrue(password_policy_enforced())

    def test_strict_rules_apply(self):
        self.assert_rejected("Abc1!", "at least 12 characters")
        self.assert_rejected(
            "Juanperez-2024!", "username", user_data={"username": "juanperez"}
        )
        self.assert_rejected("Mi clave 2024!", "whitespace")
        self.assert_accepted(GRANITO)


# --------------------------------------------------------------------------
# B. Pattern by level
# --------------------------------------------------------------------------
class _Level1PatternCases(_PatternAssertions):
    def test_valid_passwords(self):
        for password in (
            "Abc1!",
            "123!!",
            "Password1234!",
            "Mi clave 2024!",
            "Clave-20241231",
            "Abcd-19900101!",
            "Caballo-verde-taza-lampara-7!",
            GRANITO,
        ):
            with self.subTest(password=password):
                self.assert_accepted(password)
        self.assert_accepted(
            "Cornflow_admin1234",
            user_data={
                "username": "cornflow_admin",
                "email": "cornflow_admin@cornflow.com",
            },
        )
        self.assert_accepted("Juanperez-2024!", user_data={"username": "juanperez"})

    def test_invalid_passwords_with_1_3_9_messages(self):
        case_message = "Password must contain uppercase and lowercase letters."
        for password in (
            "abc1!",
            "abcdefghijkl",
            "caballo-verde-taza-lampara-7!",
            "ABCDEF1!",
        ):
            with self.subTest(password=password):
                self.assert_rejected(password, case_message, exact=True)
        self.assert_rejected(
            "Abc1", "Password must contain at least 5 characters.", exact=True
        )
        number_message = (
            "Password must contain at least one number and one special character."
        )
        for password in ("Abcdef12", "Abcdef!!"):
            with self.subTest(password=password):
                self.assert_rejected(password, number_message, exact=True)

    def test_same_result_as_1_3_9(self):
        corpus = [
            "Abc1!",
            "123!!",
            "Password1234!",
            "Mi clave 2024!",
            "Clave-20241231",
            "Abcd-19900101!",
            "Caballo-verde-taza-lampara-7!",
            GRANITO,
            "abc1!",
            "abcdefghijkl",
            "caballo-verde-taza-lampara-7!",
            "ABCDEF1!",
            "Abc1",
            "Abcdef12",
            "Abcdef!!",
            "Cornflow_admin1234",
            "Juanperez-2024!",
            "",
        ]
        rng = random.Random(1309)
        alphabet = (
            string.ascii_letters
            + string.digits
            + PASSWORD_SPECIAL_CHARACTERS
            + " "
        )
        for _ in range(500):
            length = rng.randint(0, 20)
            corpus.append("".join(rng.choice(alphabet) for _ in range(length)))
        for password in corpus:
            with self.subTest(password=password):
                self.assertEqual(
                    _check_password_pattern_1_3_9(password),
                    check_password_pattern(password),
                )

    def test_none_password_is_allowed(self):
        self.assertEqual((True, None), check_password_pattern(None))

    def test_policy_not_enforced(self):
        self.assertFalse(password_policy_enforced())

    def test_strict_flag_forces_the_policy(self):
        valid, msg = check_password_pattern("Abc1!", strict=True)
        self.assertFalse(valid)
        self.assertIn("at least 12 characters", msg)


class TestPasswordPatternLevel1(
    _Level1PatternCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1


class TestPasswordPatternLevel1MinLength(
    _PatternAssertions, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(PWD_MIN_LENGTH=6)

    def test_min_length_is_configurable(self):
        self.assert_rejected(
            "Ab3!x", "Password must contain at least 6 characters.", exact=True
        )
        self.assert_accepted("Ab3!xyzQ")


class TestPasswordPatternLevel1Zxcvbn(
    _PatternAssertions, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(PWD_MIN_ZXCVBN_SCORE=3)

    def test_zxcvbn_is_checked_when_configured(self):
        self.assert_rejected("Abc1!", "too easy to guess")
        self.assert_rejected("Password1234!", "too easy to guess")
        self.assert_accepted(GRANITO)
        # Whitespace still has no rule at level 1
        self.assert_accepted("Mi clave 2024!")


class _PolicyPatternCases(_PatternAssertions):
    def test_policy_rejections(self):
        self.assert_rejected("Abc1!", "at least 12 characters")
        self.assert_rejected("123!!", "at least 12 characters")
        self.assert_rejected("abcdefghijkl", "uppercase letter")
        self.assert_rejected("Password1234!", "too easy to guess")
        self.assert_rejected("Mi clave 2024!", "whitespace")
        self.assert_rejected("Clave-20241231", "digits")
        self.assert_rejected("Abcd-19900101!", "digits")
        self.assert_rejected(
            "Cornflow_admin1234", "username", user_data={"username": "cornflow_admin"}
        )
        self.assert_rejected(
            "Juanperez-2024!", "username", user_data={"username": "juanperez"}
        )
        self.assert_rejected("caballo-verde-taza-lampara-7!", "uppercase letter")

    def test_policy_acceptances(self):
        for password in (GRANITO, "Caballo-verde-taza-lampara-7!", P1):
            with self.subTest(password=password):
                self.assert_accepted(password)

    def test_policy_enforced(self):
        self.assertTrue(password_policy_enforced())


class TestPasswordPatternLevel2(_PolicyPatternCases, SecurityLevelTestMixin, TestCase):
    security_level = 2


class TestPasswordPatternLevel3(_PolicyPatternCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(MFA_REQUIRED=0)


class TestPasswordPatternLevel2MinLength(
    _PatternAssertions, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    security_environ = {"PWD_MIN_LENGTH": "14"}

    def test_min_length_can_be_raised(self):
        self.assert_accepted(P1)
        self.assert_rejected(P1[:-1], "at least 14")


class TestPasswordPatternLevel2MinLengthLowered(
    _PatternAssertions, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    security_environ = {"PWD_MIN_LENGTH": "6"}

    def test_min_length_can_not_be_lowered(self):
        self.assert_rejected("Ab3!xyzQ", "at least 12 characters")


# --------------------------------------------------------------------------
# C. Random passwords
# --------------------------------------------------------------------------
class TestRandomPasswordLevel1(SecurityLevelTestMixin, TestCase):
    security_level = 1

    def test_random_passwords_follow_the_policy(self):
        for _ in range(30):
            pwd = UserModel.generate_random_password()
            self.assertGreaterEqual(len(pwd), 12)
            self.assertEqual((True, None), check_password_pattern(pwd, strict=True))
            self.assertEqual((True, None), check_password_pattern(pwd, strict=False))


# --------------------------------------------------------------------------
# D. History and reuse in the model
# --------------------------------------------------------------------------
class _HistoryCases:
    def setUp(self):
        db.create_all()
        self.user = UserModel(
            {"username": "histuser", "email": "histuser@test.org", "password": P1}
        )
        self.user.save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def history_count(self):
        return UserPasswordHistoryModel.query.filter_by(user_id=self.user.id).count()


class _HistoryLevel1Cases(_HistoryCases):
    def test_same_password_is_accepted(self):
        self.user.update({"password": P1})
        self.assertEqual(1, self.history_count())

    def test_previous_password_is_accepted(self):
        self.user.update({"password": P2})
        self.user.update({"password": P1})
        self.assertEqual(2, self.history_count())


class TestPasswordHistoryLevel1(
    _HistoryLevel1Cases, SecurityLevelTestMixin, TestCase
):
    security_level = 1


class TestPasswordHistoryTrimLevel1(
    _HistoryCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(PWD_HISTORY_SIZE=2)

    def test_history_is_trimmed(self):
        for password in (P2, P3, P1, P2):
            self.user.update({"password": password})
        self.assertEqual(2, self.history_count())


class TestPasswordHistoryNegativeSizeLevel1(
    _HistoryCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(PWD_HISTORY_SIZE=-1)

    def test_negative_history_size(self):
        self.user.update({"password": P2})
        self.user.update({"password": P3})
        self.assertEqual(0, self.history_count())


class _HistoryPolicyCases(_HistoryCases):
    def test_same_password_is_rejected(self):
        with self.assertRaises(InvalidCredentials) as ctx:
            self.user.update({"password": P1})
        self.assertIn("last 10", ctx.exception.error)

    def test_previous_password_is_rejected(self):
        self.user.update({"password": P2})
        with self.assertRaises(InvalidCredentials) as ctx:
            self.user.update({"password": P1})
        self.assertIn("last 10", ctx.exception.error)

    def test_history_is_kept(self):
        self.user.update({"password": P2})
        self.assertEqual(1, self.history_count())


class TestPasswordHistoryLevel2(_HistoryPolicyCases, SecurityLevelTestMixin, TestCase):
    security_level = 2


class TestPasswordHistoryLevel3(_HistoryPolicyCases, SecurityLevelTestMixin, TestCase):
    security_level = 3
    config_overrides = _overrides(MFA_REQUIRED=0)


# --------------------------------------------------------------------------
# E. Change of the own password through the API
# --------------------------------------------------------------------------
class _ApiCases:
    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user(self, username, password, role=VIEWER_ROLE):
        user = UserModel(
            {"username": username, "email": f"{username}@test.org", "password": password}
        )
        user.save()
        UserRoleModel({"user_id": user.id, "role_id": role}).save()
        return user

    def login(self, password, username="regular", expected=200):
        response = self.client.post(
            LOGIN_URL,
            data=json.dumps({"username": username, "password": password}),
            headers=JSON_HEADER,
        )
        self.assertEqual(expected, response.status_code, response.json)
        return response.json.get("token")

    def change(self, token, payload, user_id=None):
        user_id = user_id or self.user.id
        return self.client.put(
            USER_URL + f"{user_id}/",
            data=json.dumps(payload),
            headers={**JSON_HEADER, "Authorization": "Bearer " + token},
        )

    def history_count(self):
        return UserPasswordHistoryModel.query.filter_by(user_id=self.user.id).count()


class _OwnPasswordChangeCases(_ApiCases):
    def setUp(self):
        super().setUp()
        self.user = self.create_user("regular", P1)

    def error(self, response):
        return response.json["error"].lower()


class _OwnPasswordChangeLevel1Cases(_OwnPasswordChangeCases):
    def test_without_current_password(self):
        token = self.login(P1)
        self.assertEqual(200, self.change(token, {"password": P2}).status_code)
        self.login(P2)

    def test_wrong_current_password_is_not_checked(self):
        token = self.login(P1)
        response = self.change(token, {"password": P2, "current_password": "wrong"})
        self.assertEqual(200, response.status_code)
        self.login(P2)

    def test_correct_current_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": P2, "current_password": P1})
        self.assertEqual(200, response.status_code)

    def test_same_password(self):
        token = self.login(P1)
        self.assertEqual(200, self.change(token, {"password": P1}).status_code)

    def test_back_to_previous_password(self):
        token = self.login(P1)
        self.assertEqual(200, self.change(token, {"password": P2}).status_code)
        token = self.login(P2)
        self.assertEqual(200, self.change(token, {"password": P1}).status_code)
        self.assertEqual(2, self.history_count())

    def test_similar_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": CLOSE_P1})
        self.assertEqual(200, response.status_code)

    def test_weak_1_3_9_password(self):
        token = self.login(P1)
        self.assertEqual(200, self.change(token, {"password": "Abc1!"}).status_code)
        self.login("Abc1!")


class TestOwnPasswordChangeLevel1(
    _OwnPasswordChangeLevel1Cases, SecurityLevelTestMixin, TestCase
):
    security_level = 1


class TestOwnPasswordChangeSimilarityLevel1(
    _OwnPasswordChangeCases, SecurityLevelTestMixin, TestCase
):
    security_level = 1
    config_overrides = _overrides(PWD_MAX_SIMILARITY=0.5)

    def test_similarity_not_checked_even_if_set(self):
        token = self.login(P1)
        response = self.change(token, {"password": HALF_P1, "current_password": P1})
        self.assertEqual(200, response.status_code)


class _OwnPasswordChangePolicyCases(_OwnPasswordChangeCases):
    def test_without_current_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": P2})
        self.assertEqual(400, response.status_code)
        self.assertIn("current password is missing or incorrect", self.error(response))
        self.login(P1)

    def test_wrong_current_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": P2, "current_password": "wrong"})
        self.assertEqual(400, response.status_code)
        self.assertIn("current password is missing or incorrect", self.error(response))
        self.login(P1)

    def test_correct_current_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": HALF_P1, "current_password": P1})
        self.assertEqual(200, response.status_code)

    def test_same_password(self):
        # The similarity check of the endpoint runs before the reuse check of
        # the model and the ratio of identical passwords is 1.0, so the answer
        # is the similarity message (the responses of levels 2 and 3 do not
        # change). The "last 10" message of the reuse is covered by
        # test_back_to_previous_password and by the model tests.
        token = self.login(P1)
        response = self.change(token, {"password": P1, "current_password": P1})
        self.assertEqual(400, response.status_code)
        self.assertIn("too similar", self.error(response))

    def test_back_to_previous_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": P2, "current_password": P1})
        self.assertEqual(200, response.status_code)
        token = self.login(P2)
        response = self.change(token, {"password": P1, "current_password": P2})
        self.assertEqual(400, response.status_code)
        self.assertIn("last 10", self.error(response))

    def test_similar_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": CLOSE_P1, "current_password": P1})
        self.assertEqual(400, response.status_code)
        self.assertIn("too similar", self.error(response))

    def test_weak_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": "Abc1!", "current_password": P1})
        self.assertEqual(400, response.status_code)
        self.assertIn("at least 12 characters", self.error(response))


class TestOwnPasswordChangeLevel2(
    _OwnPasswordChangePolicyCases, SecurityLevelTestMixin, TestCase
):
    security_level = 2


class TestOwnPasswordChangeLevel3(
    _OwnPasswordChangePolicyCases, SecurityLevelTestMixin, TestCase
):
    security_level = 3
    config_overrides = _overrides(MFA_REQUIRED=0)


class TestOwnPasswordChangeLevel2Similarity(
    _OwnPasswordChangeCases, SecurityLevelTestMixin, TestCase
):
    security_level = 2
    config_overrides = _overrides(PWD_MAX_SIMILARITY=0.5)

    def test_lower_threshold_rejects_a_less_similar_password(self):
        token = self.login(P1)
        response = self.change(token, {"password": HALF_P1, "current_password": P1})
        self.assertEqual(400, response.status_code)
        self.assertIn("too similar", self.error(response))


# --------------------------------------------------------------------------
# F. Sign up and password set by an admin
# --------------------------------------------------------------------------
class _SignupAndAdminCases(_ApiCases):
    # Level 1 accepts the weak 1.3.9 passwords, level 2 does not
    weak_status = 200
    weak_signup_status = 201

    def signup(self, username, password):
        return self.client.post(
            SIGNUP_URL,
            data=json.dumps(
                {
                    "username": username,
                    "email": f"{username}@test.org",
                    "password": password,
                }
            ),
            headers=JSON_HEADER,
        )

    def test_signup(self):
        response = self.signup("nuevo1", "Abc1!")
        self.assertEqual(self.weak_signup_status, response.status_code)
        if self.weak_signup_status == 201:
            self.login("Abc1!", username="nuevo1")
        self.assertEqual(400, self.signup("nuevo2", "abc1!").status_code)

    def test_admin_sets_weak_password(self):
        self.create_user("boss", P1, role=ADMIN_ROLE)
        self.user = self.create_user("ana", P2)
        token = self.login(P1, username="boss")
        response = self.change(token, {"password": "Abc1!"}, user_id=self.user.id)
        self.assertEqual(self.weak_status, response.status_code)
        token = self.login(P1, username="boss")
        response = self.change(token, {"password": GRANITO}, user_id=self.user.id)
        self.assertEqual(200, response.status_code)


class TestSignupAndAdminLevel1(_SignupAndAdminCases, SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = _overrides(SIGNUP_ACTIVATED=1)
    weak_status = 200
    weak_signup_status = 201


class TestSignupAndAdminLevel2(_SignupAndAdminCases, SecurityLevelTestMixin, TestCase):
    security_level = 2
    config_overrides = _overrides(SIGNUP_ACTIVATED=1)
    weak_status = 400
    weak_signup_status = 400


# --------------------------------------------------------------------------
# G. CLI and environment passwords
# --------------------------------------------------------------------------
def _level_overrides(level, **extra):
    overrides = dict(extra)
    if level == 3:
        overrides.setdefault("MFA_REQUIRED", 0)
    return overrides


def _reset_db():
    db.session.remove()
    db.drop_all()
    db.create_all()


class TestCliPasswordsByLevel(TestCase):
    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_viewer(self, level, username, password):
        name = security_level_config(level, **_level_overrides(level))
        with mock.patch.dict(os.environ, {"FLASK_ENV": name}):
            return CliRunner().invoke(
                cli,
                [
                    "users",
                    "create",
                    "viewer",
                    "-u",
                    username,
                    "-p",
                    password,
                    "-e",
                    f"{username}@test.org",
                ],
            )

    def exists(self, username):
        db.session.remove()
        return UserModel.get_one_user_by_username(username) is not None

    def test_cli_create_viewer(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                result = self.create_viewer(level, "admin", "adminpassword")
                self.assertNotEqual(0, result.exit_code)
                self.assertFalse(self.exists("admin"))

                # One user name per level: the database is not emptied
                # between levels. The password contains the user name.
                personal = f"admin2l{level}"
                result = self.create_viewer(level, personal, f"Admin2l{level}_pass1")
                if level == 1:
                    self.assertEqual(0, result.exit_code, result.output)
                    self.assertTrue(self.exists(personal))
                else:
                    self.assertNotEqual(0, result.exit_code)
                    self.assertIsInstance(result.exception, InvalidCredentials)
                    self.assertIn("username", result.exception.error)
                    self.assertFalse(self.exists(personal))

                viewer = f"viewer{level}"
                result = self.create_viewer(level, viewer, GRANITO)
                self.assertEqual(0, result.exit_code, result.output)
                self.assertTrue(self.exists(viewer))

    def test_create_user_with_role_default_admin_password(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                _reset_db()
                access_init_command(verbose=False)
                name = security_level_config(level, **_level_overrides(level))
                app = create_app(name)
                with app.app_context():
                    args = (
                        "cornflow_admin",
                        "cornflow_admin@cornflow.com",
                        "Cornflow_admin1234",
                        "admin",
                        ADMIN_ROLE,
                    )
                    if level == 1:
                        create_user_with_role(*args)
                        self.assertIsNotNone(
                            UserModel.get_one_user_by_username("cornflow_admin")
                        )
                    else:
                        with self.assertLogs(app.logger, "ERROR") as logs:
                            with self.assertRaises(InvalidCredentials) as ctx:
                                create_user_with_role(*args)
                        self.assertIn(INVALID_PWD_MESSAGE, ctx.exception.error)
                        self.assertTrue(
                            any(
                                "Could not create user cornflow_admin" in line
                                for line in logs.output
                            ),
                            logs.output,
                        )
                        self.assertIsNone(
                            UserModel.get_one_user_by_username("cornflow_admin")
                        )


# --------------------------------------------------------------------------
# H. service init
# --------------------------------------------------------------------------
class TestServiceInitPasswords(TestCase):
    # The class of task002 is reached through its module so that unittest does
    # not collect (and run again) its tests from this module.
    ADMIN_PWD = "Cornflow_admin1234"
    SERVICE_PWD = "Service_user1234"

    run_init = startup.TestServiceInitSecurity.run_init
    gunicorn_started = staticmethod(startup.TestServiceInitSecurity.gunicorn_started)

    def create_app(self):
        return create_app("testing")

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_level_1_default_passwords_start(self):
        result, system, _ = self.run_init(1)
        self.assertEqual(0, result.exit_code, result.output)
        for username in ("cornflow_admin", "service_user"):
            self.assertIsNotNone(UserModel.get_one_user_by_username(username))
        self.assertTrue(self.gunicorn_started(system))

    def test_levels_2_and_3_default_passwords_stop(self):
        for level in (2, 3):
            with self.subTest(level=level):
                _reset_db()
                result, system, _ = self.run_init(level, **_level_overrides(level))
                self.assertNotEqual(0, result.exit_code)
                self.assertIsInstance(result.exception, InvalidCredentials)
                self.assertEqual(0, UserModel.query.count())
                self.assertFalse(self.gunicorn_started(system))

    def test_existing_admin_is_not_validated(self):
        access_init_command(verbose=False)
        admin = UserModel(
            {
                "username": "cornflow_admin",
                "email": "cornflow_admin@cornflow.com",
                "password": GRANITO,
            }
        )
        admin.password = bcrypt.generate_password_hash("Cornflow_admin1234").decode(
            "utf8"
        )
        admin.save()
        UserRoleModel({"user_id": admin.id, "role_id": ADMIN_ROLE}).save()
        old_hash = admin.password

        result, system, _ = self.run_init(
            2, extra_env={"CORNFLOW_SERVICE_PWD": "Mimbre-Faro-Ciervo4"}
        )
        self.assertEqual(0, result.exit_code, result.output)
        self.assertTrue(self.gunicorn_started(system))
        db.session.remove()
        admin = UserModel.get_one_user_by_username("cornflow_admin")
        self.assertEqual(old_hash, admin.password)

    def test_platform_admin_password_by_level(self):
        extra_env = {
            "CORNFLOW_ADMIN_PWD": GRANITO,
            "CORNFLOW_SERVICE_PWD": "Mimbre-Faro-Ciervo4",
            "CORNFLOW_PLATFORM_ADMIN_USER": "platform_admin",
            "CORNFLOW_PLATFORM_ADMIN_PWD": "Abc1!",
        }
        result, system, _ = self.run_init(1, extra_env=extra_env)
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIsNotNone(UserModel.get_one_user_by_username("platform_admin"))
        self.assertTrue(self.gunicorn_started(system))

        _reset_db()
        result, system, _ = self.run_init(2, extra_env=extra_env)
        self.assertNotEqual(0, result.exit_code)
        self.assertIsInstance(result.exception, InvalidCredentials)
        self.assertIsNone(UserModel.get_one_user_by_username("platform_admin"))
        self.assertFalse(self.gunicorn_started(system))


if __name__ == "__main__":
    unittest.main()
