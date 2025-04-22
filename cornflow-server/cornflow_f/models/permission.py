"""
Permission model definition
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from cornflow_f.models.base import BaseModel


class PermissionViewRoleModel(BaseModel):
    """
    Model to store the permissions between actions, views, and roles
    """

    __tablename__ = "permission_view"
    __table_args__ = (UniqueConstraint("action_id", "api_view_id", "role_id"),)

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    action_id = Column(
        Integer, ForeignKey("actions.id", ondelete="CASCADE"), nullable=False
    )
    api_view_id = Column(
        Integer, ForeignKey("api_view.id", ondelete="CASCADE"), nullable=False
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    action = relationship("ActionModel", back_populates="permissions")
    view = relationship("ViewModel", back_populates="permissions")
    role = relationship("RoleModel", back_populates="permissions")

    @classmethod
    def get_permission(cls, db: Session, **kwargs):
        """
        Check if a permission exists with the given parameters
        """
        permission = db.query(cls).filter_by(deleted_at=None, **kwargs).first()
        return permission

    @classmethod
    def get_by_ids(cls, db: Session, role_id: int, action_id: int, api_view_id: int):
        """
        Check if a permission exists with the given parameters
        """
        permission = (
            db.query(cls)
            .filter_by(
                deleted_at=None,
                role_id=role_id,
                action_id=action_id,
                api_view_id=api_view_id,
            )
            .first()
        )
        return permission

    def __repr__(self):
        """
        String representation of the permission
        """
        return f"<Permission role: {self.role_id}, action: {self.action_id}, view: {self.api_view_id}>"
