from .meta_model import EmptyModel
from ..shared.const import ADMIN_ROLE, SUPER_ADMIN_ROLE
from ..shared.utils import db


class RoleModel(EmptyModel):
    __tablename__ = "roles"

    id = db.Column(db.Integer, db.Sequence("roles_id_sq"), primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __repr__(self):
        return self.name


class UserRoleModel(EmptyModel):
    __tablename__ = "user_role"

    id = db.Column(db.Integer, db.Sequence("user_roles_id_sq"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel")

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel")

    @staticmethod
    def get_one_user(user_id):
        return UserRoleModel.query.filter_by(user_id=user_id).first()

    @staticmethod
    def is_admin(user_id):
        user_roles = UserRoleModel.query.filter_by(user_id=user_id).all()
        for role in user_roles:
            if role.role_id == ADMIN_ROLE or role.role_id == SUPER_ADMIN_ROLE:
                return True

        return False

    @staticmethod
    def is_super_admin(user_id):
        user_roles = UserRoleModel.query.filter_by(user_id=user_id).all()
        for role in user_roles:
            if role.role_id == SUPER_ADMIN_ROLE:
                return True

        return False

    def __repr__(self):
        return self.user.name + " has role " + self.role.name
