"""
Models defined for the roles and the assignation of roles to users.
"""

from cornflow_core.models import RoleBaseModel

# Import from internal modules
from cornflow_core.shared import db


class RoleModel(RoleBaseModel):
    # TODO: Should have a user_id to store the user that defined the role?
    __tablename__ = "roles"

    user_roles = db.relationship(
        "UserRoleModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleModel.id==UserRoleModel.role_id, "
        "UserRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleModel.id==PermissionViewRoleModel.role_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
