from .meta_model import TraceAttributes
from ..shared.utils import db


class PermissionViewRoleModel(TraceAttributes):
    __tablename__ = "permission_view"
    __table_args__ = (db.UniqueConstraint("action_id", "api_view_id", "role_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    action_id = db.Column(db.Integer, db.ForeignKey("actions.id"), nullable=False)
    action = db.relationship("ActionModel")

    api_view_id = db.Column(db.Integer, db.ForeignKey("api_view.id"), nullable=True)
    api_view = db.relationship("ApiViewModel")

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel")

    def __init__(self, data):
        super().__init__()
        self.action_id = data.get("action_id")
        self.api_view_id = data.get("api_view_id")
        self.role_id = data.get("role_id")

    @staticmethod
    def get_permission(role_id, view_id, action_id):
        permission = PermissionViewRoleModel.query.filter_by(
            role_id=role_id,
            api_view_id=view_id,
            action_id=action_id,
            deleted_at=None,
        ).first()

        if permission is not None:
            return True

    @staticmethod
    def get_all_objects():
        return PermissionViewRoleModel.query.all()

    def __repr__(self):
        representation = (
            self.role.name
            + " "
            + self.action_id.name.replace("_", " ")
            + " on "
            + self.api_view.name
        )
        return representation
