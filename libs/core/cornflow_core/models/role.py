"""

"""

from cornflow_core.models import TraceAttributesModel
from cornflow_core.shared import db


class RoleBaseModel(TraceAttributesModel):
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

    def __init__(self, data):
        super().__init__()
        self.id = data.get("id")
        self.name = data.get("name")

    def __repr__(self):
        return f"<Role {self.name}>"

    def __str__(self):
        return self.__repr__()
