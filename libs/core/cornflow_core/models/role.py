"""
This file contains the RoleBaseModel
"""

from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class RoleBaseModel(TraceAttributesModel):
    """
    This model has the roles that are defined on the REST API
    It inherits from :class:`TraceAttributesModel` to have trace fields

    The :class:`RoleBaseModel` has the following fields:

    - **id**: int, the primary key of the table, an integer value that is auto incremented
    - **name**: str, the name of the role
    - **created_at**: datetime, the datetime when the user was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the user was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the user was deleted (in UTC).
      This field is used only if we deactivate instead of deleting the record.
      This datetime is generated automatically, the user does not need to provide it.
    """

    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)

    user_roles = db.relationship(
        "UserRoleBaseModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleBaseModel.id==UserRoleBaseModel.role_id, "
        "UserRoleBaseModel.deleted_at==None)",
        cascade="all,delete",
    )

    permissions = db.relationship(
        "PermissionViewRoleBaseModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleBaseModel.id==PermissionViewRoleBaseModel.role_id, "
        "PermissionViewRoleBaseModel.deleted_at==None)",
        cascade="all,delete",
    )

    def __init__(self, data):
        super().__init__()
        self.id = data.get("id")
        self.name = data.get("name")

    def __repr__(self):
        return f"<Role {self.name}>"

    def __str__(self):
        return self.__repr__()
