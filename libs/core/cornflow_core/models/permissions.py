"""
This file contains the PermissionViewRoleBaseModel
"""

from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class PermissionViewRoleBaseModel(TraceAttributesModel):
    """
    This model has the permissions that can be defined between an action, a view and a role
    It inherits from :class:`TraceAttributesModel` to have trace fields

    The :class:`PermissionViewRoleBaseModel` has the following fields:

    - **id**: int, the primary key of the table, an integer value that is auto incremented
    - **action_id**: the id of the action
    - **api_view_id**: the id of the api view
    - **role_id**: the id of the role
    - **created_at**: datetime, the datetime when the user was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the user was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the user was deleted (in UTC).
      This field is used only if we deactivate instead of deleting the record.
      This datetime is generated automatically, the user does not need to provide it.

    """

    # TODO: trace the user that modifies the permissions
    __tablename__ = "permission_view"
    __table_args__ = (db.UniqueConstraint("action_id", "api_view_id", "role_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    action_id = db.Column(db.Integer, db.ForeignKey("actions.id"), nullable=False)
    action = db.relationship("ActionBaseModel", viewonly=True)

    api_view_id = db.Column(db.Integer, db.ForeignKey("api_view.id"), nullable=False)
    api_view = db.relationship("ViewBaseModel", viewonly=True)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleBaseModel", viewonly=True)

    def __init__(self, data):
        super().__init__()
        self.action_id = data.get("action_id")
        self.api_view_id = data.get("api_view_id")
        self.role_id = data.get("role_id")

    @classmethod
    def get_permission(cls, **kwargs: dict) -> bool:
        """
        Method to check if there is permissions with the combination of fields that are in the keyword arguments

        :param dict kwargs: the keyword arguments to search for
        :return: if there are permissions or not
        :rtype: bool
        """
        permission = cls.query.filter_by(deleted_at=None, **kwargs).first()
        if permission is not None:
            return True
        else:
            return False

    def __repr__(self):
        return f"<Permission role: {self.role_id}, action: {self.action_id}, view: {self.api_view_id}>"
