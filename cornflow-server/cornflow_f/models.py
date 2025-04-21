from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from cornflow_f.database import Base


class User(Base):
    """
    User model with all required fields
    """

    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # UUID field
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid4()))

    # Optional name fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Required fields
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

    # Timestamp fields
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at = Column(DateTime, nullable=True)

    # Self-referential foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationship
    user = relationship("User", remote_side=[id], backref="subordinates")

    @classmethod
    def get_by_username(cls, db, username: str):
        """
        Get a user by username
        """
        return db.query(cls).filter(cls.username == username).first()

    @classmethod
    def get_by_email(cls, db, email: str):
        """
        Get a user by email
        """
        return db.query(cls).filter(cls.email == email).first()

    @classmethod
    def exists_by_username(cls, db, username: str) -> bool:
        """
        Check if a username already exists
        """
        return cls.get_by_username(db, username) is not None

    @classmethod
    def exists_by_email(cls, db, email: str) -> bool:
        """
        Check if an email already exists
        """
        return cls.get_by_email(db, email) is not None
