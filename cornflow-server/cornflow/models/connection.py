from cornflow.models.meta_models import EmptyBaseModel
from cornflow.shared import db
from datetime import datetime


class ConnectionModel(EmptyBaseModel):
    """
    Model to store the session ids of the connected clients
    This model inherits from :class:`EmptyBaseModel` and does not have traceability

    The fields for this model are:

    - **id**: an integer value to represent the action
    - **user_id**: the id of the user
    - **session_id**: the id of the session
    """

    __tablename__ = "connection"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(256), nullable=False, primary_key=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("UserModel", viewonly=True)

    def __init__(self, data):
        super().__init__()
        self.session_id = data.get("session_id")
        self.user_id = data.get("user_id")
        self.created_at = datetime.utcnow()
        self.expires_at = data.get("expires_at")

    def is_expired(self):
        return self.expires_at < datetime.utcnow()

    def __repr__(self):
        return f"<Connection {self.id}>"

    def __str__(self):
        return self.__repr__()
