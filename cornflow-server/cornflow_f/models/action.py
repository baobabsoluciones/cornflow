"""
Action model definition
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship, Session
from cornflow_f.models.base import BaseModel


class ActionModel(BaseModel):
    """
    Model to store the actions that can be performed over the REST API: get, patch, post, put, delete.
    """

    __tablename__ = "actions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Action name (e.g., 'can_get', 'can_post', etc.)
    name = Column(String(128), unique=True, nullable=False)

    # Description of the action
    description = Column(Text, nullable=True)

    # Relationship with permissions
    permissions = relationship(
        "PermissionViewRoleModel", back_populates="action", cascade="all, delete-orphan"
    )

    @classmethod
    def get_by_name(cls, db: Session, name: str):
        """
        Get an action by name
        """
        return db.query(cls).filter(cls.name == name, cls.deleted_at.is_(None)).first()

    @classmethod
    def exists_by_name(cls, db: Session, name: str) -> bool:
        """
        Check if an action name already exists
        """
        return cls.get_by_name(db, name) is not None

    def __repr__(self):
        """
        String representation of the action
        """
        return f"<Action {self.id}: {self.name}>"
