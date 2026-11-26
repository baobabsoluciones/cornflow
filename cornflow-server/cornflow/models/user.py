"""
This file contains the UserModel
"""

# Imports from external libraries
import random
import string
from datetime import datetime, timedelta, timezone

# Cryptographically secure random generator for password generation
_secure_random = random.SystemRandom()

from flask import current_app

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.models.user_password_history import UserPasswordHistoryModel
from cornflow.models.user_role import UserRoleModel
from cornflow.shared import (
    bcrypt,
    db,
)
from cornflow.shared.audit import audit
from cornflow.shared.const import (
    API_KEY_SCOPE_FULL,
    DEFAULT_LOGIN_MAX_ATTEMPTS,
    DEFAULT_PWD_HISTORY_SIZE,
    PASSWORD_SPECIAL_CHARACTERS,
)
from cornflow.shared.encryption import decrypt_value, encrypt_value
from cornflow.shared.exceptions import InvalidCredentials
from cornflow.shared.validators import (
    check_password_pattern,
    check_email_pattern,
    password_policy_enforced,
)


class UserModel(TraceAttributesModel):
    """
    Model class for the Users.
    It inherits from :class:`TraceAttributes` to have trace fields.

    The class :class:`UserModel` has the following fields:

    - **id**: int, the user id, primary key for the users.
    - **first_name**: str, the name of the user.
    - **last_name**: str, the name of the user.
    - **username**: str, the username of the user used for the login.
    - **email**: str, the email of the user.
    - **password**: str, the hashed password of the user.
    - **created_at**: datetime, the datetime when the execution was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the execution was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the execution was deleted (in UTC). Even though it is deleted,
      actually, it is not deleted from the database, in order to have a command that cleans up deleted data
      after a certain time of its deletion.
      This datetime is generated automatically, the user does not need to provide it.

    :param dict data: the parsed json got from and endpoint that contains all the required information to
      create a new user.
    """

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    pwd_last_change = db.Column(db.DateTime, nullable=True)
    pwd_change_required = db.Column(db.Boolean, nullable=False, default=False)
    totp_secret = db.Column(db.String(256), nullable=True)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked = db.Column(db.Boolean, nullable=False, default=False)
    # Incremented on security events (password change, lock, MFA reset) to
    # invalidate every outstanding session token of the user
    token_version = db.Column(db.Integer, nullable=False, default=0)
    # Version embedded in the personal API key. Bumped to revoke previous
    # keys (one active key per user), on explicit revoke, on account lock
    # and on MFA reset. Not affected by routine password changes.
    api_key_version = db.Column(db.Integer, nullable=False, default=0)
    # When the active personal API key was issued: the key itself is never
    # stored (shown once), only this timestamp, so the expiry can be computed
    # and notified. NULL when there is no active key (or it predates this).
    api_key_issued_at = db.Column(db.DateTime, nullable=True)
    # Scope of the active key: "full" or "read" (read-only). NULL == full.
    api_key_scope = db.Column(db.String(16), nullable=True)
    # Smallest expiry threshold (in days) already notified for the active key,
    # so each notice is sent once. Reset when a new key is issued.
    api_key_expiry_notified = db.Column(db.Integer, nullable=True)
    # Rotation grace: the version of the key replaced by the current one and
    # the instant until which it is still accepted, so automation can be
    # redeployed after generating the new key without a gap.
    api_key_previous_version = db.Column(db.Integer, nullable=True)
    api_key_grace_until = db.Column(db.DateTime, nullable=True)
    # Last accepted TOTP time-step, to reject replay of the same or an older
    # code within its validity window
    totp_last_counter = db.Column(db.Integer, nullable=True)
    # Timestamp of the last successful login (shown to the user)
    last_login_at = db.Column(db.DateTime, nullable=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

    user_roles = db.relationship("UserRoleModel", cascade="all,delete", backref="users")

    # Refresh-token sessions are removed with the user (they carry a FK to it)
    sessions = db.relationship(
        "SessionModel", cascade="all,delete", backref="users"
    )

    instances = db.relationship(
        "InstanceModel",
        backref="users",
        lazy=True,
        primaryjoin="and_(UserModel.id==InstanceModel.user_id, "
        "InstanceModel.deleted_at==None)",
        cascade="all,delete",
    )

    cases = db.relationship(
        "CaseModel",
        backref="users",
        lazy=True,
        primaryjoin="and_(UserModel.id==CaseModel.user_id, CaseModel.deleted_at==None)",
        cascade="all,delete",
    )

    dag_permissions = db.relationship(
        "PermissionsDAG",
        cascade="all,delete",
        backref="users",
        primaryjoin="and_(UserModel.id==PermissionsDAG.user_id)",
    )

    @property
    def roles(self):
        """
        This property gives back the roles assigned to the user
        """
        return {r.role.id: r.role.name for r in self.user_roles}

    def __init__(self, data):
        super().__init__()
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        self.pwd_last_change = datetime.now(timezone.utc)
        self.pwd_change_required = bool(data.get("pwd_change_required", False))
        self.totp_secret = None
        self.mfa_enabled = False
        self.failed_login_attempts = 0
        self.locked = False
        self.token_version = 0
        self.totp_last_counter = None
        self.last_login_at = None
        self.api_key_version = 0
        # TODO: handle better None passwords that can be found when using ldap
        check_pass, msg = check_password_pattern(
            data.get("password"), user_data=data
        )
        if check_pass:
            self.password = self.__generate_hash(data.get("password"))
        else:
            raise InvalidCredentials(
                msg, log_txt="Error while trying to create a new user. " + msg
            )

        check_email, msg = check_email_pattern(data.get("email"))
        if check_email:
            self.email = data.get("email")
        else:
            raise InvalidCredentials(
                msg, log_txt="Error while trying to create a new user. " + msg
            )

    def _password_context(self, data: dict = None) -> dict:
        """
        Builds the personal information dict used to validate that a new
        password does not contain the user's data. Values sent on the update
        take precedence over the stored ones.

        :param dict data: the incoming update data
        :return: dict with username, first_name, last_name and email
        :rtype: dict
        """
        data = data or {}
        return {
            key: data.get(key) or getattr(self, key, None)
            for key in ("username", "first_name", "last_name", "email")
        }

    @staticmethod
    def _password_history_size() -> int:
        """
        Number of previous passwords kept. Never negative, as level 1 has no
        limits on PWD_HISTORY_SIZE.
        """
        return max(
            int(current_app.config.get("PWD_HISTORY_SIZE", DEFAULT_PWD_HISTORY_SIZE)),
            0,
        )

    def check_password_reuse(self, new_password: str) -> bool:
        """
        Checks if the given password matches the current password or any of
        the stored previous ones.

        :param str new_password: the candidate password
        :return: True if the password was already used
        :rtype: bool
        """
        history_size = self._password_history_size()
        hashes = []
        if self.password:
            hashes.append(self.password)
        if self.id is not None:
            hashes.extend(
                UserPasswordHistoryModel.get_last_hashes(self.id, history_size)
            )
        return any(
            bcrypt.check_password_hash(stored_hash, new_password)
            for stored_hash in hashes
        )

    def update(self, data):
        """
        Updates the user information in the database

        :param dict data: the data to update the user
        """
        # First we create the hash of the new password and then we update the object
        new_password = data.get("password")
        if new_password:
            check_pass, msg = check_password_pattern(
                new_password, user_data=self._password_context(data)
            )
            if not check_pass:
                raise InvalidCredentials(
                    msg,
                    log_txt=f"Error while trying to update user {self.id}. " + msg,
                )
            if password_policy_enforced() and self.check_password_reuse(new_password):
                err = (
                    "The new password can not be one of the last "
                    f"{self._password_history_size()} "
                    "passwords used."
                )
                raise InvalidCredentials(
                    err,
                    log_txt=f"Error while trying to update user {self.id}. " + err,
                )
            # The replaced hash is stored at every security level, even if the
            # reuse check only runs from level 2
            if self.password and self.id is not None:
                UserPasswordHistoryModel(
                    {"user_id": self.id, "password_hash": self.password}
                ).save()
                UserPasswordHistoryModel.trim_history(
                    self.id, self._password_history_size()
                )
            new_password = self.__generate_hash(new_password)
            data["password"] = new_password
            data["pwd_last_change"] = datetime.now(timezone.utc)
            # Changing the password clears any pending forced change unless
            # the caller states otherwise (e.g. an admin reset)
            data.setdefault("pwd_change_required", False)
            # A password change revokes every outstanding session token
            data["token_version"] = (self.token_version or 0) + 1
        super().update(data)

    def comes_from_external_provider(self):
        """
        Returns a boolean if the user comes from an external_provider or not
        """
        return self.password is None

    @staticmethod
    def __generate_hash(password):
        """
        Method to generate the hash from the password.

        :param str password: the password given by the user .
        :return: the hashed password.
        :rtype: str
        """
        if password is None:
            return None
        # rounds omitted on purpose: Flask-Bcrypt uses BCRYPT_LOG_ROUNDS
        return bcrypt.generate_password_hash(password).decode("utf8")

    def check_hash(self, password):
        """
        Method to check if the hash stored in the database is the same as the password given by the user

        :param str password: the password given by the user.
        :return: if the password is the same or not.
        :rtype: bool
        """
        return bcrypt.check_password_hash(self.password, password)

    def is_login_locked(self) -> bool:
        """
        Returns True while the account is locked because of too many
        consecutive failed login attempts. The lock does not expire: the
        account stays locked until it is unlocked through the API or the
        break-glass CLI command, also when the lockout is later disabled
        (LOGIN_MAX_ATTEMPTS=0).

        :rtype: bool
        """
        return bool(self.locked)

    @staticmethod
    def login_max_attempts() -> int:
        """
        Consecutive failed logins (wrong password or wrong second-factor code)
        that lock an account, as configured with LOGIN_MAX_ATTEMPTS. A value of
        0 or lower means there is no lockout and failures are not counted (the
        default at security level 1, where the setting has no limits).
        """
        return int(
            current_app.config.get("LOGIN_MAX_ATTEMPTS", DEFAULT_LOGIN_MAX_ATTEMPTS)
        )

    @staticmethod
    def login_lockout_enabled() -> bool:
        """
        Returns True when failed logins lock accounts (LOGIN_MAX_ATTEMPTS
        above 0).
        """
        return UserModel.login_max_attempts() > 0

    def _lock_after_failed_logins(self, max_attempts: int):
        """
        Locks the account after max_attempts consecutive failed logins. Locking
        revokes every outstanding session (token version and refresh-token
        sessions) and the personal API key, with no rotation grace, at every
        security level. The lock does not expire. Added to the session but not
        committed (the calling flow commits).
        """
        self.locked = True
        self.revoke_all_sessions()
        self._clear_api_key_state()
        current_app.logger.warning(
            f"User {self.username} locked after {max_attempts} failed login "
            f"attempts. An administrator must unlock the account."
        )
        audit(
            "account.locked",
            outcome="locked",
            target_id=self.id,
            target=self.username,
            attempts=self.failed_login_attempts,
        )

    def register_failed_login(self):
        """
        Registers a failed login attempt (wrong password or wrong TOTP code).
        With LOGIN_MAX_ATTEMPTS above 0, the account is locked once that many
        consecutive failures are reached and stays locked until it is unlocked
        (there is no automatic unlock). With LOGIN_MAX_ATTEMPTS at 0 or lower
        (the default at security level 1) failures are neither counted nor
        lock the account; accounts that were already locked stay locked.
        Service users are exempt from the lockout so the machine-to-machine
        communication can not be denial-of-serviced.
        """
        if self.is_service_user():
            current_app.logger.warning(
                f"Failed login attempt for service user {self.username}"
            )
            return
        max_attempts = self.login_max_attempts()
        if max_attempts <= 0:
            return
        # Incremented in the database, not read-modify-write, so that a burst
        # of parallel failures can not try more than max_attempts passwords
        # before the lock. The commit reloads the counter on the object.
        model = type(self)
        model.query.filter(model.id == self.id).update(
            {
                "failed_login_attempts": db.func.coalesce(
                    model.failed_login_attempts, 0
                )
                + 1
            },
            synchronize_session=False,
        )
        db.session.commit()
        if not self.locked and self.failed_login_attempts >= max_attempts:
            self._lock_after_failed_logins(max_attempts)
        db.session.add(self)
        db.session.commit()

    def reset_failed_login(self):
        """
        Clears the failed login counter after a successful authentication.
        """
        if self.failed_login_attempts:
            self.failed_login_attempts = 0
            db.session.add(self)
            db.session.commit()

    def unlock_account(self):
        """
        Unlocks the account and clears the failed login counter. Called by the
        unlock endpoint (platform administrators, and at security levels 1 and 2
        also the client admin for users without platform roles) and by the
        break-glass CLI command.
        """
        self.locked = False
        self.failed_login_attempts = 0
        db.session.add(self)
        db.session.commit()

    def revoke_all_sessions(self):
        """
        Invalidates every outstanding session token of the user by bumping
        the token version embedded in the tokens, and revokes the stored
        refresh-token sessions so they can no longer be rotated. The change is
        added to the session but not committed (the calling flow commits).
        """
        self.token_version = (self.token_version or 0) + 1
        db.session.add(self)
        # Also revoke the stateful refresh-token sessions (imported lazily to
        # avoid a circular import at module load).
        from cornflow.models.session import SessionModel

        SessionModel.revoke_all_for_user(self.id)

    def rotate_api_key(self, scope: str = None):
        """
        Bumps the API key version so the previously issued personal API key is
        superseded (one active key per user), records the issue timestamp and
        the scope, and commits. The new key itself is signed afterwards by the
        auth layer with the new version.

        When a rotation grace window is configured the superseded key stays
        valid for that long, so a key wired into running automation can be
        replaced without a gap: generate first, redeploy after.

        :param str scope: scope of the new key (API_KEY_SCOPE_FULL / _READ)
        """
        previous_version = self.api_key_version or 0
        grace_minutes = int(
            current_app.config.get("API_KEY_ROTATION_GRACE_MINUTES", 0)
        )
        self.api_key_version = previous_version + 1
        self.api_key_issued_at = datetime.now(timezone.utc)
        self.api_key_scope = scope or API_KEY_SCOPE_FULL
        self.api_key_expiry_notified = None
        if grace_minutes > 0 and self.api_key_issued_at is not None:
            self.api_key_previous_version = previous_version
            self.api_key_grace_until = datetime.now(timezone.utc) + timedelta(
                minutes=grace_minutes
            )
        else:
            self.api_key_previous_version = None
            self.api_key_grace_until = None
        db.session.add(self)
        db.session.commit()

    def _clear_api_key_state(self):
        """
        Invalidates the user's personal API key, including the key superseded by
        the last rotation that may still be inside its grace window. Added to
        the session but not committed (the calling flow commits).
        """
        self.api_key_version = (self.api_key_version or 0) + 1
        self.api_key_issued_at = None
        self.api_key_scope = None
        self.api_key_expiry_notified = None
        self.api_key_previous_version = None
        self.api_key_grace_until = None
        db.session.add(self)

    def revoke_api_keys(self):
        """
        Invalidates the user's personal API key without issuing a new one
        (explicit disable, and on account lock / MFA reset). The rotation
        grace does not apply here: an explicit revocation is immediate.
        """
        self._clear_api_key_state()
        db.session.commit()

    def api_key_expires_at(self):
        """
        Expiry instant of the active personal API key, or None when there is
        no active key (or it was issued before the timestamp was tracked).

        :rtype: datetime or None
        """
        if self.api_key_issued_at is None:
            return None
        issued_at = self.api_key_issued_at
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        return issued_at + timedelta(
            days=int(current_app.config["API_KEY_DURATION_DAYS"])
        )

    def api_key_days_left(self):
        """
        Whole days left before the active API key expires (may be negative if
        it already expired), or None when there is no active key.

        :rtype: int or None
        """
        expires_at = self.api_key_expires_at()
        if expires_at is None:
            return None
        delta = expires_at - datetime.now(timezone.utc)
        return int(delta.total_seconds() // 86400)

    def is_api_key_in_grace(self, version: int) -> bool:
        """
        Whether the given API key version is the one superseded by the current
        key and is still inside the rotation grace window.

        :param int version: the version claim of the presented key
        :rtype: bool
        """
        if self.api_key_previous_version is None or self.api_key_grace_until is None:
            return False
        if int(version) != int(self.api_key_previous_version):
            return False
        grace_until = self.api_key_grace_until
        if grace_until.tzinfo is None:
            grace_until = grace_until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) <= grace_until

    def set_totp_secret(self, secret: str):
        """
        Stores the TOTP secret of the user encrypted at rest.

        :param str secret: the plain base32 TOTP secret (None to clear it)
        """
        self.totp_secret = encrypt_value(secret)

    def get_totp_secret(self) -> str:
        """
        Returns the plain TOTP secret of the user.

        :return: the base32 TOTP secret or None if not set
        :rtype: str
        """
        return decrypt_value(self.totp_secret)

    def check_totp_code(self, code: str, enforce_replay: bool = True) -> bool:
        """
        Verifies a TOTP code against the secret of the user.

        When ``enforce_replay`` is True (the login path) a code from the same
        or an older time-step than the last accepted one is rejected, and the
        accepted step is recorded. A ±1 step window is allowed for clock
        drift. During enrollment (``enforce_replay`` False) the code is only
        validated: the replay counter is left untouched so the user can log
        in with a fresh code right after enrolling.

        :param str code: the 6 digit code from the authenticator app
        :param bool enforce_replay: whether to enforce and record the
          anti-replay counter
        :return: True if the code is valid (and not a replay when enforced)
        :rtype: bool
        """
        import time

        import pyotp

        secret = self.get_totp_secret()
        if not secret or not code:
            return False
        code = str(code).strip()
        totp = pyotp.TOTP(secret)
        interval = 30
        now = int(time.time())
        current_step = now // interval
        # Check the current step and its immediate neighbours (clock drift)
        for step in (current_step, current_step - 1, current_step + 1):
            if totp.at(step * interval) == code:
                if not enforce_replay:
                    return True
                if (
                    self.totp_last_counter is not None
                    and step <= self.totp_last_counter
                ):
                    # The code (or an older one) was already used
                    return False
                # Conditional update, so that two concurrent requests with
                # the same code can not both pass the check above: only the
                # one that moves the counter forward is accepted
                model = type(self)
                claimed = model.query.filter(
                    model.id == self.id,
                    db.or_(
                        model.totp_last_counter.is_(None),
                        model.totp_last_counter < step,
                    ),
                ).update({"totp_last_counter": step}, synchronize_session=False)
                db.session.commit()
                return claimed == 1
        return False

    @classmethod
    def get_all_users(cls):
        """
        Query to get all users

        :return: a list with all the users.
        :rtype: list(:class:`UserModel`)
        """
        return cls.get_all_objects()

    @classmethod
    def get_one_user(cls, idx):
        """
        Query to get the information of one user

        :param int idx: ID of the user
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(idx=idx)

    @classmethod
    def get_one_user_by_email(cls, email):
        """
        Query to get one user from the email

        :param str email: User email
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(email=email)

    @classmethod
    def get_one_user_by_username(cls, username):
        """
        Returns one user (object) given a username

        :param str username: the user username that we want to query for
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(username=username)

    def check_username_in_use(self):
        """
        Checks if a username is already in use

        :return: a boolean if the username is in use
        :rtype: bool
        """
        return self.query.filter_by(username=self.username).first() is not None

    def check_email_in_use(self):
        """
        Checks if a email is already in use

        :return: a boolean if the username is in use
        :rtype: bool
        """
        return self.query.filter_by(email=self.email).first() is not None

    @staticmethod
    def generate_random_password() -> str:
        """
        Method to generate a new random password for the user

        :return: the newly generated password
        :rtype: str
        """
        while True:
            nb_lower = _secure_random.randint(4, 9)
            nb_upper = _secure_random.randint(max(10 - nb_lower, 4), 11)
            nb_numbers = _secure_random.randint(1, 3)
            nb_special_char = _secure_random.randint(1, 3)
            upper_letters = _secure_random.sample(string.ascii_uppercase, nb_upper)
            lower_letters = _secure_random.sample(string.ascii_lowercase, nb_lower)
            numbers = _secure_random.sample(list(map(str, list(range(10)))), nb_numbers)
            symbols = _secure_random.sample(
                PASSWORD_SPECIAL_CHARACTERS, nb_special_char
            )
            chars = upper_letters + lower_letters + numbers + symbols
            _secure_random.shuffle(chars)
            pwd = "".join(chars)
            # Random passwords always follow the full policy, whatever the
            # security level
            check, _ = check_password_pattern(pwd, strict=True)
            if check:
                return pwd

    def is_admin(self):
        """
        Returns a boolean if a user is an admin or not
        """
        return UserRoleModel.is_admin(self.id)

    def is_service_user(self):
        """
        Returns a boolean if a user is a service user or not
        """
        return UserRoleModel.is_service_user(self.id)

    def is_platform_admin(self):
        """
        Returns a boolean if a user is a platform administrator or not
        """
        return UserRoleModel.is_platform_admin(self.id)

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)

    def __str__(self):
        return self.__repr__()
