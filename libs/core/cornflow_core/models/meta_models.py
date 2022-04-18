"""

"""
import datetime
import logging as log

from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_core.shared import database
from abc import ABC


class EmptyBaseModel(database.Model, ABC):
    __abstract__ = True

    def commit_changes(self, action: str = None):
        if action is None:
            action = ""

        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on {action} new data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on {action} new data: {e}")
            log.error(f"Data: {self}")

    def save(self):
        database.session.add(self)
        self.commit_changes("saving")

    def delete(self):
        database.session.delete(self)
        self.commit_changes("deleting")

    def update(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        database.session.add(self)
        self.commit_changes("updating")

    @classmethod
    def get_all_objects(cls, **kwargs):
        return cls.query.filter_by(**kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        if idx is None:
            return cls.get_all_objects(**kwargs).first()
        return cls.query.get(idx)


class TraceAttributesModel(EmptyBaseModel):
    __abstract__ = True
    created_at = database.Column(database.DateTime, nullable=False)
    updated_at = database.Column(database.DateTime, nullable=False)
    deleted_at = database.Column(database.DateTime, nullable=True)

    def __init__(self):
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None

    def update(self, data):
        self.updated_at = datetime.datetime.utcnow()
        super().update(data)

    def disable(self):
        self.deleted_at = datetime.datetime.utcnow()
        database.session.add(self)
        self.commit_changes("disabling")

    def activate(self):
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None
        database.session.add(self)
        self.commit_changes("activating")

    @classmethod
    def get_all_objects(cls, **kwargs):
        return super().get_all_objects(deleted_at=None, **kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        if idx is None:
            return cls.get_all_objects(**kwargs).first()
        return cls.query.get(idx)
