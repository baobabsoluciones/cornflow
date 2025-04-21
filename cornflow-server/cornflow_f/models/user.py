"""
User model definition
"""

from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Session
from cornflow_f.database import Base
from cornflow_f.models.base import BaseModel
from cornflow_f.security import get_password_hash, verify_password


class UserModel(BaseModel):
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

    # Relationships
    user = relationship("UserModel", remote_side=[id], backref="subordinates")
    user_roles = relationship(
        "UserRoleModel", back_populates="user", cascade="all, delete-orphan"
    )

    def __init__(self, **data):
        """
        Initialize a new user with the given data
        """
        if "password" in data:
            data["password"] = get_password_hash(data["password"])
        super().__init__(**data)

    def update(self, db: Session, data: dict) -> None:
        """
        Update user information (PUT operation)
        """
        if "password" in data:
            data["password"] = get_password_hash(data["password"])
        super().update(db, data)

    def patch(self, db: Session, data: dict) -> None:
        """
        Partially update user information (PATCH operation)
        """
        if "password" in data:
            data["password"] = get_password_hash(data["password"])
        super().patch(db, data)

    def verify_password(self, plain_password: str) -> bool:
        """
        Verify if the given password matches the user's password
        """
        return verify_password(plain_password, self.password)

    def get_roles(self, db: Session):
        """
        Get all roles for this user
        """
        from cornflow_f.models.user_role import UserRoleModel

        return UserRoleModel.get_user_roles(db, self.id)

    def has_role(self, db: Session, role_id: int) -> bool:
        """
        Check if user has a specific role
        """
        from cornflow_f.models.user_role import UserRoleModel

        return UserRoleModel.has_role(db, self.id, role_id)

    @classmethod
    def get_by_username(cls, db: Session, username: str):
        """
        Get a user by username
        """
        return (
            db.query(cls)
            .filter(cls.username == username, cls.deleted_at.is_(None))
            .first()
        )

    @classmethod
    def get_by_email(cls, db: Session, email: str):
        """
        Get a user by email
        """
        return (
            db.query(cls).filter(cls.email == email, cls.deleted_at.is_(None)).first()
        )

    @classmethod
    def exists_by_username(cls, db: Session, username: str) -> bool:
        """
        Check if a username already exists
        """
        return cls.get_by_username(db, username) is not None

    @classmethod
    def exists_by_email(cls, db: Session, email: str) -> bool:
        """
        Check if an email already exists
        """
        return cls.get_by_email(db, email) is not None
