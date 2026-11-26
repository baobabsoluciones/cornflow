"""
The single-use checks (TOTP anti-replay counter, backup codes and refresh
token rotation) must hold when two requests with the same code or token run
at the same time.

The race is reproduced by committing the competing request's write between
the moment the code reads the row and the moment it writes it: with a
read-then-write both requests are accepted, with a conditional update only
the first one is.
"""

import time
import unittest
from unittest import mock

import pyotp
from flask_testing import TestCase

from cornflow.commands.access import access_init_command
from cornflow.models import MFABackupCodeModel, SessionModel, UserModel, UserRoleModel
from cornflow.shared import bcrypt, db
from cornflow.shared.authentication import Auth
from cornflow.shared.const import VIEWER_ROLE
from cornflow.shared.exceptions import InvalidToken
from cornflow.tests.security_levels_support import SecurityLevelTestMixin

PASSWORD = "Kx9#tR2m!Qw7Zp"


class TestAtomicClaims(SecurityLevelTestMixin, TestCase):
    security_level = 1
    config_overrides = {"REFRESH_TOKEN_ENABLED": 1}

    def setUp(self):
        db.create_all()
        access_init_command(verbose=False)
        self.user = UserModel(
            {"username": "ana", "email": "ana@test.org", "password": PASSWORD}
        )
        self.user.save()
        UserRoleModel({"user_id": self.user.id, "role_id": VIEWER_ROLE}).save()
        self.secret = pyotp.random_base32()
        self.user.set_totp_secret(self.secret)
        self.user.mfa_enabled = True
        self.user.save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def current_step(self):
        return int(time.time()) // 30

    # TOTP
    def test_totp_code_is_accepted_once(self):
        code = pyotp.TOTP(self.secret).now()
        self.assertTrue(self.user.check_totp_code(code))
        self.assertFalse(self.user.check_totp_code(code))

    def test_concurrent_totp_replay_is_rejected(self):
        code = pyotp.TOTP(self.secret).now()
        user = UserModel.get_one_user(self.user.id)
        # This request has read the counter (still empty)...
        self.assertIsNone(user.totp_last_counter)
        # ...when a concurrent request with the same code stores its step
        UserModel.query.filter_by(id=user.id).update(
            {"totp_last_counter": self.current_step() + 1},
            synchronize_session=False,
        )
        self.assertFalse(user.check_totp_code(code))

    # Backup codes
    def test_backup_code_is_single_use(self):
        MFABackupCodeModel({"user_id": self.user.id, "code": "abcde12345"}).save()
        self.assertTrue(MFABackupCodeModel.try_consume(self.user.id, "abcde12345"))
        db.session.commit()
        self.assertFalse(MFABackupCodeModel.try_consume(self.user.id, "abcde12345"))

    def test_concurrent_backup_code_use_is_rejected(self):
        row = MFABackupCodeModel({"user_id": self.user.id, "code": "abcde12345"})
        row.save()
        row_id = row.id
        real_check = bcrypt.check_password_hash

        def check_then_lose_the_race(code_hash, code):
            matched = real_check(code_hash, code)
            if matched:
                # A concurrent request consumes the same code right after
                # this one has found it among the unused codes
                MFABackupCodeModel.query.filter_by(id=row_id).update(
                    {"used_at": db.func.now()}, synchronize_session=False
                )
            return matched

        with mock.patch.object(
            bcrypt, "check_password_hash", side_effect=check_then_lose_the_race
        ):
            self.assertFalse(
                MFABackupCodeModel.try_consume(self.user.id, "abcde12345")
            )

    # Refresh token rotation
    def test_refresh_token_rotates_once(self):
        tokens = Auth.issue_session_tokens(self.user)
        new_tokens = Auth.consume_refresh_token(tokens["refresh_token"])
        self.assertNotEqual(tokens["refresh_token"], new_tokens["refresh_token"])
        with self.assertRaises(InvalidToken):
            Auth.consume_refresh_token(tokens["refresh_token"])

    def test_concurrent_refresh_with_the_same_token_is_reuse(self):
        tokens = Auth.issue_session_tokens(self.user)
        real_is_expired = SessionModel.is_expired

        def rotated_meanwhile(session):
            # A concurrent refresh with the same token rotates the session
            # after this request checked the jti
            SessionModel.query.filter_by(id=session.id).update(
                {"jti": "rotated-by-the-other-request"}, synchronize_session=False
            )
            return real_is_expired(session)

        with mock.patch.object(
            SessionModel, "is_expired", autospec=True, side_effect=rotated_meanwhile
        ):
            with self.assertRaises(InvalidToken):
                Auth.consume_refresh_token(tokens["refresh_token"])
        db.session.expire_all()
        session = SessionModel.query.filter_by(user_id=self.user.id).first()
        self.assertTrue(session.revoked)
        self.assertEqual("rotated-by-the-other-request", session.jti)


if __name__ == "__main__":
    unittest.main()
