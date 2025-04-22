"""
View model definition
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship, Session
from cornflow_f.models.base import BaseModel


class ViewModel(BaseModel):
    """
    Model to store the views/endpoints/resources of the API
    """

    __tablename__ = "api_view"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # View name (e.g., 'users', 'items', etc.)
    name = Column(String(128), unique=True, nullable=False)

    # URL rule for the view (e.g., '/api/v1/users')
    path = Column(String(128), nullable=False)

    # Description of the view
    description = Column(Text, nullable=True)

    # Relationship with permissions
    permissions = relationship(
        "PermissionViewRoleModel", back_populates="view", cascade="all, delete-orphan"
    )

    @classmethod
    def get_by_name(cls, db: Session, name: str):
        """
        Get a view by name
        """
        return db.query(cls).filter(cls.name == name, cls.deleted_at.is_(None)).first()

    @classmethod
    def get_by_path(cls, db: Session, path: str):
        """
        Get a view by URL rule
        """
        return db.query(cls).filter(cls.path == path, cls.deleted_at.is_(None)).first()

    @classmethod
    def exists_by_name(cls, db: Session, name: str) -> bool:
        """
        Check if a view name already exists
        """
        return cls.get_by_name(db, name) is not None

    @classmethod
    def exists_by_path(cls, db: Session, path: str) -> bool:
        """
        Check if a view with the given path already exists
        """
        return cls.get_by_path(db, path) is not None

    def __repr__(self):
        """
        String representation of the view
        """
        return f"<View {self.name}>"
