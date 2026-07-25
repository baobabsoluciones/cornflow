"""
This file contains the UserPasswordHistoryModel, used to store the previous
password hashes of the users so old passwords can not be reused.
"""

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.shared import db


class UserPasswordHistoryModel(TraceAttributesModel):
    """
    Model class to store the hashes of the passwords previously used by each
    user. It inherits from :class:`TraceAttributesModel` to have trace fields.

    - **id**: int, the primary key.
    - **user_id**: int, the id of the user the hash belongs to.
    - **password_hash**: str, the bcrypt hash of the old password.
    """

    __tablename__ = "user_password_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, data):
        super().__init__()
        self.user_id = data.get("user_id")
        self.password_hash = data.get("password_hash")

    @classmethod
    def get_last_hashes(cls, user_id: int, limit: int) -> list:
        """
        Gets the most recent stored password hashes for a user.

        :param int user_id: the id of the user
        :param int limit: maximum number of hashes to return
        :return: the list of hashes, most recent first
        :rtype: list
        """
        rows = (
            cls.query.filter_by(user_id=user_id)
            .order_by(cls.id.desc())
            .limit(limit)
            .all()
        )
        return [row.password_hash for row in rows]

    @classmethod
    def trim_history(cls, user_id: int, keep: int):
        """
        Deletes the stored hashes of a user beyond the most recent `keep` ones.
        The deletion is added to the current session but not committed.

        :param int user_id: the id of the user
        :param int keep: number of hashes to keep
        """
        ids_to_delete = [
            row.id
            for row in cls.query.filter_by(user_id=user_id)
            .order_by(cls.id.desc())
            .offset(keep)
            .all()
        ]
        if ids_to_delete:
            cls.query.filter(cls.id.in_(ids_to_delete)).delete(
                synchronize_session=False
            )

    def __repr__(self):
        return f"<UserPasswordHistory user {self.user_id}>"
