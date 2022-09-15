"""
This file contains the base abstract models from which the rest of the models inherit
"""
import logging as log
from datetime import datetime
from typing import Dict, List

from sqlalchemy.exc import DBAPIError, IntegrityError

from cornflow_core.exceptions import InvalidData
from cornflow_core.shared import db


class EmptyBaseModel(db.Model):
    """
    This is an empty abstract model that just implements some basic logic to be shared across all models.
    """

    __abstract__ = True

    def commit_changes(self, action: str = None):
        """
        This method is in charge to commit the changes to the database and perform a rollback in case there is an error,
        raising then an class:`InvalidData` exception

        :param str action: the action that is being performed
        :return: None
        :rtype: None
        """
        if action is None:
            action = ""

        try:
            db.session.commit()
            log.debug(f"Transaction type: {action}, performed correctly on {self}")
        except IntegrityError as err:
            db.session.rollback()
            log.error(f"Integrity error on {action} data: {err}")
            log.error(f"Data: {self.__dict__}")
            raise InvalidData(f"Integrity error on {action} with data {self}")
        except DBAPIError as err:
            db.session.rollback()
            log.error(f"Unknown database error on {action} data: {err}")
            log.error(f"Data: {self.__dict__}")
            raise InvalidData(f"Unknown database error on {action} with data {self}")
        except Exception as err:
            db.session.rollback()
            log.error(f"Unknown error on {action} data: {err}")
            log.error(f"Data: {self.__dict__}")
            raise InvalidData(f"Unknown error on {action} with data {self}")

    def save(self):
        """
        Method used to save a new object to the database

        :return: None
        :rtype: None
        """
        db.session.add(self)
        self.commit_changes("saving")

    def delete(self):
        """
        Method used to delete an object from the database

        :return: None
        :rtype: None
        """
        db.session.delete(self)
        self.commit_changes("deleting")

    def update(self, data: Dict):
        """
        Method used to update an object from the database

        :param dict data: the data of the object
        :return: None
        :rtype: None
        """
        self.pre_update(data)
        db.session.add(self)
        self.commit_changes("updating")

    def pre_update(self, data: Dict):
        """
        Method used to update the values of an object but not write it to the database
        :param dict data: the data of the object
        :return: None
        :rtype: None
        """
        for key, value in data.items():
            setattr(self, key, value)

    @classmethod
    def create_bulk(cls, data: List):
        instances = [cls(item) for item in data]
        db.session.add_all(instances)
        action = "bulk create"
        try:
            db.session.commit()
            log.debug(f"Transaction type: {action}, performed correctly on {cls}")
        except IntegrityError as err:
            db.session.rollback()
            log.error(f"Integrity error on {action} data: {err}")
            raise InvalidData(f"Integrity error on {action} with data {cls}")
        except DBAPIError as err:
            db.session.rollback()
            log.error(f"Unknown database error on {action} data: {err}")
            raise InvalidData(f"Unknown database error on {action} with data {cls}")
        except Exception as err:
            db.session.rollback()
            log.error(f"Unknown error on {action} data: {err}")
            raise InvalidData(f"Unknown error on {action} with data {cls}")
        return instances

    @classmethod
    def create_update_bulk(cls, instances):
        db.session.add_all(instances)
        action = "bulk create update"
        try:
            db.session.commit()
            log.debug(f"Transaction type: {action}, performed correctly on {cls}")
        except IntegrityError as err:
            db.session.rollback()
            log.error(f"Integrity error on {action} data: {err}")
            raise InvalidData(f"Integrity error on {action} with data {cls}")
        except DBAPIError as err:
            db.session.rollback()
            log.error(f"Unknown database error on {action} data: {err}")
            raise InvalidData(f"Unknown database error on {action} with data {cls}")
        except Exception as err:
            db.session.rollback()
            log.error(f"Unknown error on {action} data: {err}")
            raise InvalidData(f"Unknown error on {action} with data {cls}")
        return instances

    @classmethod
    def get_all_objects(cls, **kwargs):
        """
        Method to get all the objects from the database applying the filters passed as keyword arguments

        :param kwargs: the keyword arguments to be used as filters
        :return: the query without being performed until and object is going to be retrieved or
        iterated through the results.
        :rtype: class:`Query`
        """
        return cls.query.filter_by(**kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        """
        Method to retrieve an specific object from the database. This object can be retrieved with the primary key id
        or with a set of filters that should give back just one object, because the method is going
        to pick the first one. An example would be to filter by a column that has a unique constraint.

        :param str | int idx: the id value for the primary key
        :param kwargs: the keyword arguments passed to filter
        :return: the retrieved object
        :rtype: class:`Model` or any class that inherits from it
        """
        if idx is None:
            return cls.query.filter_by(**kwargs).first()
        return cls.query.filter_by(id=idx, **kwargs).first()

    def get(self, key: str):
        """
        Method used to get the value of any attribute of the model

        :param str key: the attribute that we want to get the value from.
        :return: the value of the given attribute
        :rtype: Any
        """
        value = getattr(self, key, None)
        return value


class TraceAttributesModel(EmptyBaseModel):
    """
    This abstract model is used to create the trace columns on all dependent models.

    The trace columns are:

    - **created_at**: datetime, the datetime when the user was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the user was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the user was deleted (in UTC).
      This field is used only if we deactivate instead of deleting the record.
      This datetime is generated automatically, the user does not need to provide it.
    """

    __abstract__ = True
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __init__(self):
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.deleted_at = None

    def update(self, data):
        """
        Method used to update an object from the database

        :param dict data: the data of the object
        :return: None
        :rtype: None
        """
        self.updated_at = datetime.utcnow()
        super().update(data)

    def pre_update(self, data):
        self.updated_at = datetime.utcnow()
        super().pre_update(data)

    def disable(self):
        """
        Method used to deactivate an object on the database (set the deleted_at date to the actual time stamp)

        :return: None
        :rtype: None
        """
        self.deleted_at = datetime.utcnow()
        db.session.add(self)
        self.commit_changes("disabling")

    def activate(self):
        """
        Method used to activate an object on the database (set the deleted_at date to None)

        :return: None
        :rtype: None
        """
        self.updated_at = datetime.utcnow()
        self.deleted_at = None
        db.session.add(self)
        self.commit_changes("activating")

    @classmethod
    def get_all_objects(cls, **kwargs):
        """
        Method to get all the objects from the database applying the filters passed as keyword arguments

        :param kwargs: the keyword arguments to be used as filters
        :return: the query without being performed until and object is going to be retrieved or
        iterated through the results.
        :rtype: class:`Query`
        """
        kwargs.update(deleted_at=None)
        return super().get_all_objects(**kwargs)

    @classmethod
    def get_one_object(cls, idx=None, **kwargs):
        """
        Method to retrieve an specific object from the database. This object can be retrieved with the primary key id
        or with a set of filters that should give back just one object, because the method is going
        to pick the first one. An example would be to filter by a column that has a unique constraint.

        :param str | int idx: the id value for the primary key
        :param kwargs: the keyword arguments passed to filter
        :return: the retrieved object
        :rtype: class:`Model` or any class that inherits from it
        """
        kwargs.update(deleted_at=None)
        return super().get_one_object(idx=idx, **kwargs)
