"""
This file contains the RoleModel
"""
# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from sqlalchemy import func

from cornflow.shared import db
from cornflow.shared.const import RESERVED_ROLE_RANGE


class RoleModel(TraceAttributesModel):
    """
    This model has the roles that are defined on the REST API
    It inherits from :class:`TraceAttributesModel` to have trace fields

    The :class:`RoleModel` has the following fields:

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

    def __init__(self, data):
        super().__init__()
        self.id = data.get("id")
        self.name = data.get("name")

    @classmethod
    def next_free_id_below_reserved_range(cls):
        """
        Id for a new role created without an explicit id: the highest id below
        the reserved range (900-999) plus one, counting also the soft-deleted
        roles, so a new role never lands among the platform roles (a role
        stored there under another name stops the next start, see
        check_reserved_role_ids). None if there is no free id below the range.
        """
        low, _ = RESERVED_ROLE_RANGE
        highest = db.session.query(func.max(cls.id)).filter(cls.id < low).scalar()
        candidate = 0 if highest is None else highest + 1
        return candidate if candidate < low else None

    def __repr__(self):
        return f"<Role {self.name}>"

    def __str__(self):
        return self.__repr__()
