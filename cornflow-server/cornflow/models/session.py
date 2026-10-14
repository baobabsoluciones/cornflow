"""
This file contains the SessionModel: the stateful store behind the
refresh-token sessions (ENS op.acc — session management).

Each row is one interactive session. It holds the current refresh-token id
(``jti``, rotated on every refresh), the moment of the last activity (to
enforce the sliding inactivity window) and the absolute expiry (the hard cap
on the session lifetime). Storing sessions server-side lets us revoke a single
session, detect refresh-token reuse (a theft signal) and reason about
inactivity independently of the JWT's own expiry.
"""

import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app

from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import db


def _as_utc(value: datetime) -> datetime:
    """
    Normalises a datetime read back from the database to a timezone-aware UTC
    datetime (SQLite returns naive datetimes), so it can be compared with
    ``datetime.now(timezone.utc)``.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _new_id() -> str:
    return uuid.uuid4().hex


class SessionModel(TraceAttributesModel):
    """
    Model for an interactive refresh-token session.

    - **id**: int, primary key.
    - **session_id**: str, stable identifier of the logical session (survives
      refresh-token rotation); carried in the ``sid`` claim of refresh tokens.
    - **jti**: str, id of the *current* refresh token; rotated on each
      refresh. A refresh token whose ``jti`` no longer matches has been
      superseded — presenting it again is treated as reuse.
    - **user_id**: int, the owner.
    - **last_activity_at**: datetime, updated on each refresh (sliding
      inactivity window).
    - **expires_at**: datetime, absolute hard cap of the session.
    - **revoked**: bool, whether the session has been revoked (logout, reuse
      detection, or a global revocation).
    """

    __tablename__ = "session_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    jti = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    last_activity_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, data):
        super().__init__()
        now = datetime.now(timezone.utc)
        self.user_id = data.get("user_id")
        self.session_id = data.get("session_id") or _new_id()
        self.jti = data.get("jti") or _new_id()
        self.last_activity_at = data.get("last_activity_at") or now
        self.expires_at = data.get("expires_at")
        self.revoked = False

    @classmethod
    def create_for_user(cls, user) -> "SessionModel":
        """
        Creates and persists a new session for a user, with a fresh
        session_id / jti and the absolute expiry taken from the config.
        Opportunistically removes the user's stale (revoked or expired)
        session rows so the table stays bounded for active users.

        :param user: the user the session belongs to
        :return: the created session
        :rtype: :class:`SessionModel`
        """
        cls.purge_stale(user_id=user.id)
        absolute_hours = int(
            current_app.config.get("REFRESH_TOKEN_ABSOLUTE_HOURS", 12)
        )
        session = cls(
            {
                "user_id": user.id,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(hours=absolute_hours),
            }
        )
        session.save()
        return session

    @classmethod
    def purge_stale(cls, user_id: int = None) -> int:
        """
        Deletes the revoked or expired session rows (for one user or for
        everyone). The deletion joins the caller's transaction: it is
        committed by the following save/commit.

        :param int user_id: optional user to restrict the purge to
        :return: the number of deleted rows
        :rtype: int
        """
        # Naive UTC now: the column is stored naive, and a timezone-aware
        # bound parameter would break the comparison on SQLite
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = cls.query.filter(
            db.or_(cls.revoked.is_(True), cls.expires_at < now)
        )
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        # "fetch" keeps the ORM identity map in sync with the bulk delete
        # (a new session row may reuse a just-deleted primary key)
        return query.delete(synchronize_session="fetch")

    @classmethod
    def get_active(cls, session_id: str) -> "SessionModel":
        """
        Returns the non-revoked, non-deleted session with this session_id, or
        None.

        :param str session_id: the logical session identifier
        :rtype: :class:`SessionModel` or None
        """
        if not session_id:
            return None
        return cls.query.filter_by(
            session_id=session_id, revoked=False, deleted_at=None
        ).first()

    def is_inactive(self) -> bool:
        """
        True if the session has had no activity for longer than the sliding
        inactivity window (`REFRESH_TOKEN_INACTIVITY_MINUTES`).
        """
        window = int(
            current_app.config.get("REFRESH_TOKEN_INACTIVITY_MINUTES", 30)
        )
        deadline = _as_utc(self.last_activity_at) + timedelta(minutes=window)
        return datetime.now(timezone.utc) > deadline

    def is_expired(self) -> bool:
        """
        True if the session has reached its absolute maximum lifetime.
        """
        return datetime.now(timezone.utc) > _as_utc(self.expires_at)

    def rotate(self) -> str:
        """
        Issues a new refresh-token id for this session and refreshes the
        activity timestamp (sliding window). Returns the new jti.

        :rtype: str
        """
        self.jti = _new_id()
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        db.session.add(self)
        self.commit_changes("rotating session")
        return self.jti

    def revoke(self):
        """Marks the session as revoked (idempotent)."""
        if not self.revoked:
            self.revoked = True
            self.updated_at = datetime.now(timezone.utc)
            db.session.add(self)
            self.commit_changes("revoking session")

    @classmethod
    def revoke_all_for_user(cls, user_id: int):
        """
        Marks every active session of a user as revoked. Added to the session
        and committed by the caller (used from the user's global session
        revocation).

        :param int user_id: the id of the user
        """
        cls.query.filter_by(user_id=user_id, revoked=False).update(
            {"revoked": True}, synchronize_session=False
        )

    def __repr__(self):
        return f"<Session {self.session_id} user {self.user_id}>"
