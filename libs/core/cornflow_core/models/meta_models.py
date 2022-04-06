"""

"""
import datetime
import logging as log
from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_backend.shared import database


class EmptyBaseModel(database.Model):
    __abstract__ = True

    def save(self):
        database.session.add(self)
        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on saving new data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on saving new data: {e}")
            log.error(f"Data: {self}")

    def delete(self):
        database.session.delete(self)

        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on deleting existing data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on deleting existing data: {e}")
            log.error(f"Data: {self}")

    def update(self, data):
        database.session.add(self)
        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on updating data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on updating data: {e}")
            log.error(f"Data: {self}")


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

        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on disabling data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on disabling data: {e}")
            log.error(f"Data: {self}")

    def activate(self):
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None
        database.session.add(self)

        try:
            database.session.commit()
        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on activating data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on activating data: {e}")
            log.error(f"Data: {self}")
