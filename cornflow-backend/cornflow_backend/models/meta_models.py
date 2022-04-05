"""

"""
import datetime
import logging as log
from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_backend.shared import db


class EmptyBaseModel(db.Model):
    __abstract__ = True

    def save(self):
        db.session.add(self)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on saving new data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on saving new data: {e}")
            log.error(f"Data: {self}")

    def delete(self):
        db.session.delete(self)

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on deleting existing data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on deleting existing data: {e}")
            log.error(f"Data: {self}")

    def update(self, data):
        db.session.add(self)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on updating data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on updating data: {e}")
            log.error(f"Data: {self}")


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

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on disabling data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on disabling data: {e}")
            log.error(f"Data: {self}")

    def activate(self):
        self.updated_at = datetime.datetime.utcnow()
        self.deleted_at = None
        db.session.add(self)

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            log.error(f"Integrity error on activating data: {e}")
            log.error(f"Data: {self}")
        except DBAPIError as e:
            db.session.rollback()
            log.error(f"Unknown error on activating data: {e}")
            log.error(f"Data: {self}")
