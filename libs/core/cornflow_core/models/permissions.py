"""

"""

from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class PermissionViewRoleBaseModel(TraceAttributesModel):
    """ """

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
    def get_permission(cls, **kwargs):
        """

        :param dict kwargs:
        :return:
        :rtype:
        """
        permission = cls.query.filter_by(deleted_at=None, **kwargs).first()
        if permission is not None:
            return True
        else:
            return False

    def __repr__(self):
        return f"<Permission role: {self.role_id}, action: {self.action_id}, view: {self.api_view_id}>"
