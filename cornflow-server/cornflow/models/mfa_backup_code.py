"""
This file contains the MFABackupCodeModel, used to store the hashed one-time
backup codes that let a user log in when they lose access to their
authenticator app.
"""

from datetime import datetime, timezone

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import bcrypt, db


class MFABackupCodeModel(TraceAttributesModel):
    """
    Model class to store the backup codes generated when a user enrolls in
    two-factor authentication. Codes are stored hashed and are single use.

    - **id**: int, the primary key.
    - **user_id**: int, the id of the user the code belongs to.
    - **code_hash**: str, the bcrypt hash of the backup code.
    - **used_at**: datetime, when the code was consumed (null if unused).
    """

    __tablename__ = "mfa_backup_codes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    code_hash = db.Column(db.String(128), nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, data):
        super().__init__()
        self.user_id = data.get("user_id")
        # rounds omitted on purpose: Flask-Bcrypt uses BCRYPT_LOG_ROUNDS
        self.code_hash = bcrypt.generate_password_hash(
            data.get("code")
        ).decode("utf8")
        self.used_at = None

    @classmethod
    def delete_all_for_user(cls, user_id: int):
        """
        Deletes every backup code of a user. The deletion is added to the
        current session but not committed.

        :param int user_id: the id of the user
        """
        cls.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    @classmethod
    def try_consume(cls, user_id: int, code: str) -> bool:
        """
        Checks the given code against the unused backup codes of the user and
        marks it as used when it matches. The change is committed by the
        caller through the user save/update flow.

        :param int user_id: the id of the user
        :param str code: the plain backup code provided on login
        :return: True if the code matched an unused backup code
        :rtype: bool
        """
        if not code:
            return False
        unused_codes = cls.query.filter_by(user_id=user_id, used_at=None).all()
        for row in unused_codes:
            if bcrypt.check_password_hash(row.code_hash, code):
                row.used_at = datetime.now(timezone.utc)
                db.session.add(row)
                return True
        return False

    def __repr__(self):
        return f"<MFABackupCode user {self.user_id}>"
