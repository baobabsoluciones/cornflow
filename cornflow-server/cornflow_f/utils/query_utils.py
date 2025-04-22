"""
Utility functions for database queries
"""

from typing import TypeVar, Type, List
from sqlalchemy.orm import Session
from cornflow_f.models.base import BaseModel

# Define a generic type for models that inherit from BaseDataModel
T = TypeVar("T", bound=BaseModel)


def get_all_records(
    db: Session, model_class: Type[T], include_deleted: bool = False
) -> List[T]:
    """
    Generic function to retrieve all records of a model from the database.

    :param db: Database session
    :param model_class: The model class to query
    :param include_deleted: Whether to include soft-deleted records (default: False)

    :return: List of records of the specified model
    """
    query = db.query(model_class)

    if not include_deleted:
        query = query.filter(model_class.deleted_at.is_(None))

    return query.all()


def get_one_record_internal_id(
    db: Session, model_class: Type[T], internal_id: int, include_deleted: bool = False
) -> T:
    """
    Generic function to retrieve one record of a model from the database.

    :param db: Database session
    :param model_class: The model class to query
    :param internal_id: The internal ID of the record to retrieve
    :param include_deleted: Whether to include soft-deleted records (default: False)

    :return: The record of the specified model
    """
    query = db.query(model_class)

    if not include_deleted:
        query = query.filter(model_class.deleted_at.is_(None))

    return query.filter(model_class.id == internal_id).first()


def get_one_record_external_id(
    db: Session, model_class: Type[T], external_id: str, include_deleted: bool = False
) -> T:
    """
    Generic function to retrieve one record of a model from the database.

    :param db: Database session
    :param model_class: The model class to query
    :param external_id: The external ID of the record to retrieve
    :param include_deleted: Whether to include soft-deleted records (default: False)

    :return: The record of the specified model
    """
    query = db.query(model_class)
    if not include_deleted:
        query = query.filter(model_class.deleted_at.is_(None))

    return query.filter(model_class.uuid == external_id).first()
