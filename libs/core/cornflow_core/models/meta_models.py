"""

"""
import datetime
import logging as log

from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_core.shared import db


class EmptyBaseModel(db.Model):
    __abstract__ = True

    def commit_changes(self, action: str = None):
        if action is None:
            action = ""

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on {action} new data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on {action} new data: {e}")
            log.error(f"Data: {self}")

    def save(self):
        db.session.add(self)
        self.commit_changes("saving")

    def delete(self):
        db.session.delete(self)
        self.commit_changes("deleting")

    def update(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        db.session.add(self)
        self.commit_changes("updating")

    @classmethod
    def get_all_objects(cls, **kwargs):
        return cls.query.filter_by(**kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        if idx is None:
            return cls.query.filter_by(**kwargs).first()
        return cls.query.filter_by(id=idx, **kwargs).first()

    def get(self, key):
        value = getattr(self, key, None)
        return value


class TraceAttributesModel(EmptyBaseModel):
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
        super().update(data)

    def disable(self):
        self.deleted_at = datetime.datetime.utcnow()
        db.session.add(self)
        self.commit_changes("disabling")

    def activate(self):
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None
        db.session.add(self)
        self.commit_changes("activating")

    @classmethod
    def get_all_objects(cls, **kwargs):
        kwargs.update({"deleted_at": None})
        return super().get_all_objects(**kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        kwargs.update({"deleted_at": None})
        return super().get_one_object(idx=idx, **kwargs)
