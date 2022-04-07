"""

"""
import datetime
import logging as log

from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_core.shared import database


class EmptyBaseModel(database.Model):
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
        database.session.add(self)
        self.commit_changes("updating")

    @classmethod
    def get_all_objects(cls):
        return cls.query.all()

    @classmethod
    def get_one_object(cls, idx):
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
        # TODO: avoid using setattr. Could be done as: self.__dict__.update(data)
        #  but this would create new keys, not just update the existing ones
        #  and a need to implement the __dict__ method.
        for key, item in data.items():
            setattr(self, key, item)
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
    def get_all_objects(cls, *args, **kwargs):
        return cls.query.filter_by(deleted_at=None)

    @classmethod
    def get_one_object(cls, idx):
        return cls.query.filter_by(id=idx, deleted_at=None).first()
