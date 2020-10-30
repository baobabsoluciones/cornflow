"""

"""
import datetime
from sqlalchemy.ext.declarative import declared_attr
from ..shared.utils import db


class TraceAttributes(db.Model):
    """

    """
    __abstract__ = True
    created_at = db.Column(db.DateTime)
    modified_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)

    def __init__(self):
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = datetime.datetime.utcnow()
        self.deleted_at = None

    def update(self):
        self.modified_at = datetime.datetime.utcnow()

    def delete(self):
        self.deleted_at = datetime.datetime.utcnow()


class BaseAttributes(TraceAttributes):
    """

    """
    __abstract__ = True
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    @declared_attr
    def user_id(cls):
        return db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, data):
        self.user_id = data.get('user_id')
        super().__init__()
