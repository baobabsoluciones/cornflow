"""
Role model definition
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship, Session
from cornflow_f.models.base import BaseModel


class RoleModel(BaseModel):
    """
    Role model that defines the available roles in the system
    """

    __tablename__ = "roles"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Role name
    name = Column(String(50), unique=True, index=True, nullable=False)

    # Role description
    description = Column(Text, nullable=True)

    # Relationship with UserRoleModel
    user_roles = relationship(
        "UserRoleModel", back_populates="role", cascade="all, delete-orphan"
    )

    def __init__(self, **data):
        """
        Initialize a new role with the given data
        """
        super().__init__(**data)

    @classmethod
    def get_by_name(cls, db: Session, name: str):
        """
        Get a role by name
        """
        return db.query(cls).filter(cls.name == name, cls.deleted_at.is_(None)).first()

    @classmethod
    def exists_by_name(cls, db: Session, name: str) -> bool:
        """
        Check if a role name already exists
        """
        return cls.get_by_name(db, name) is not None

    def __repr__(self):
        """
        String representation of the role
        """
        return f"<Role {self.name}>"
