"""
Base model classes for database operations
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Type, TypeVar

from fastapi import HTTPException
from sqlalchemy import Column, DateTime
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from cornflow_f.database import Base

T = TypeVar("T", bound="BaseModel")


class BaseModel(Base):
    """
    Base model class that implements common database operations and error handling.
    All models should inherit from this class.
    """

    __abstract__ = True

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    deleted_at = Column(DateTime, nullable=True)

    def __init__(self, **data):
        """
        Initialize a new object with the given data
        """
        super().__init__(**data)

    def save(self, db: Session) -> None:
        """
        Save a new object to the database

        Args:
            db: Database session

        Raises:
            HTTPException: If there is an error saving the object
        """
        try:
            db.add(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def refresh(self, db: Session) -> None:
        """
        Refresh the object from the database
        """
        db.refresh(self)

    def delete(self, db: Session) -> None:
        """
        Delete an object from the database

        Args:
            db: Database session

        Raises:
            HTTPException: If there is an error deleting the object
        """
        try:
            db.delete(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def update(self, db: Session, data: Dict) -> None:
        """
        Update an object in the database (PUT operation).
        This method will set all fields not present in data to None.

        Args:
            db: Database session
            data: Dictionary of fields to update

        Raises:
            HTTPException: If there is an error updating the object
        """
        try:
            self.updated_at = datetime.now(timezone.utc)

            # Get all column names from the model
            column_names = [c.name for c in self.__table__.columns]

            # Set all fields to None first (PUT operation)
            for column in column_names:
                if column not in ["id", "created_at", "updated_at", "deleted_at"]:
                    setattr(self, column, None)

            # Then update with provided data
            for key, value in data.items():
                if key in column_names:
                    setattr(self, key, value)

            db.add(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def patch(self, db: Session, data: Dict) -> None:
        """
        Partially update an object in the database (PATCH operation).
        Only fields present in data will be modified.

        Args:
            db: Database session
            data: Dictionary of fields to update

        Raises:
            HTTPException: If there is an error updating the object
        """
        try:
            self.updated_at = datetime.now(timezone.utc)

            # Get all column names from the model
            column_names = [c.name for c in self.__table__.columns]

            # Only update fields that are present in data
            for key, value in data.items():
                if key in column_names:
                    setattr(self, key, value)

            db.add(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def soft_delete(self, db: Session) -> None:
        """
        Soft delete an object by setting deleted_at

        Args:
            db: Database session

        Raises:
            HTTPException: If there is an error soft deleting the object
        """
        try:
            self.deleted_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
            db.add(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    def restore(self, db: Session) -> None:
        """
        Restore a soft-deleted object by setting deleted_at to None

        Args:
            db: Database session

        Raises:
            HTTPException: If there is an error restoring the object
        """
        try:
            self.deleted_at = None
            self.updated_at = datetime.now(timezone.utc)
            db.add(self)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    def get_by_id(cls: Type[T], db: Session, id: str) -> Optional[T]:
        """
        Get an object by its ID

        Args:
            db: Database session
            id: Object ID

        Returns:
            Optional[T]: The object if found, None otherwise
        """
        return db.query(cls).filter(cls.id == id, cls.deleted_at.is_(None)).first()

    @classmethod
    def get_all(
        cls: Type[T], db: Session, skip: int = 0, limit: int = 100, **filters
    ) -> List[T]:
        """
        Get all objects with optional filtering and pagination

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filters to apply

        Returns:
            List[T]: List of objects
        """
        query = db.query(cls).filter(cls.deleted_at.is_(None))
        for key, value in filters.items():
            if value is not None:
                query = query.filter(getattr(cls, key) == value)
        return query.offset(skip).limit(limit).all()

    @classmethod
    def create(cls: Type[T], db: Session, **data) -> T:
        """
        Create a new object

        Args:
            db: Database session
            **data: Object data

        Returns:
            T: The created object

        Raises:
            HTTPException: If there is an error creating the object
        """
        try:
            obj = cls(**data)
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except DBAPIError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
