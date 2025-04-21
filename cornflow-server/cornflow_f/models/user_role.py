"""
User-Role relationship model definition
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from cornflow_f.models.base import BaseModel


class UserRoleModel(BaseModel):
    """
    Model for managing the relationship between users and roles
    """

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user = relationship("UserModel", back_populates="user_roles")
    role = relationship("RoleModel", back_populates="user_roles")

    def __init__(self, **data):
        """
        Initialize a new user-role relationship
        """
        super().__init__(**data)

    @classmethod
    def get_user_roles(cls, db: Session, user_id: int):
        """
        Get all roles for a user
        """
        return (
            db.query(cls).filter(cls.user_id == user_id, cls.deleted_at.is_(None)).all()
        )

    @classmethod
    def get_role_users(cls, db: Session, role_id: int):
        """
        Get all users for a role
        """
        return (
            db.query(cls).filter(cls.role_id == role_id, cls.deleted_at.is_(None)).all()
        )

    @classmethod
    def has_role(cls, db: Session, user_id: int, role_id: int) -> bool:
        """
        Check if a user has a specific role
        """
        return (
            db.query(cls)
            .filter(
                cls.user_id == user_id, cls.role_id == role_id, cls.deleted_at.is_(None)
            )
            .first()
            is not None
        )

    def __repr__(self):
        """
        String representation of the user-role relationship
        """
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"
