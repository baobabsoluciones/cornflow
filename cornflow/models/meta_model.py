"""

"""
import datetime

from sqlalchemy.ext.declarative import declared_attr

from ..shared.utils import db


class TraceAttributes(db.Model):
    """

    """
    __abstract__ = True
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __init__(self):
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None

    def update(self, data):
        self.updated_at = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def disable(self):
        self.deleted_at = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()


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

    def update(self, data):
        self.user_id = data.get('user_id')
        super().update(data)
