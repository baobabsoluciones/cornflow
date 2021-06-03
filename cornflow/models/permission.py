from .meta_model import EmptyModel, TraceAttributes
from ..shared.utils import db


class PermissionModel(EmptyModel):
    """
    This model contains the base permissions over the REST API. These are:

    * can get
    * can patch
    * can post
    * can put
    * can delete
    """

    __tablename__ = "permissions"

    id = db.Column(db.Integer, db.Sequence("permission_id_seq"), primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __repr__(self):
        return str(self.id) + ": " + self.name


class PermissionViewRoleModel(TraceAttributes):
    __tablename__ = "permission_view"
    __table_args__ = (db.UniqueConstraint("permission_id", "api_view_id", "role_id"),)

    id = db.Column(
        db.Integer, db.Sequence("permission_view_role_id_seq"), primary_key=True
    )

    permission_id = db.Column(
        db.Integer, db.ForeignKey("permissions.id"), nullable=False
    )
    permission = db.relationship("PermissionModel")

    api_view_id = db.Column(db.Integer, db.ForeignKey("api_view.id"), nullable=True)
    api_view = db.relationship("ApiViewModel")

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel")

    def __init__(self, data):
        super().__init__()
        self.permission_id = data.get("permission_id")
        self.api_view_id = data.get("api_view_id")
        self.role_id = data.get("role_id")

    @staticmethod
    def get_permission(role_id, view_id, permission_id):
        return PermissionViewRoleModel.query.filter_by(
            role_id=role_id,
            api_view_id=view_id,
            permission_id=permission_id,
            deleted_at=None,
        ).first()

    def __repr__(self):
        representation = (
            self.role.name
            + " "
            + self.permission.name.replace("_", " ")
            + " on "
            + self.api_view.name
        )
        return representation
