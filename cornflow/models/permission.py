from .meta_model import TraceAttributes
from .dag import DeployedDAG
from ..shared.utils import db


class PermissionViewRoleModel(TraceAttributes):
    __tablename__ = "permission_view"
    __table_args__ = (db.UniqueConstraint("action_id", "api_view_id", "role_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    action_id = db.Column(db.Integer, db.ForeignKey("actions.id"), nullable=False)
    action = db.relationship("ActionModel", viewonly=True)

    api_view_id = db.Column(db.Integer, db.ForeignKey("api_view.id"), nullable=False)
    api_view = db.relationship("ApiViewModel", viewonly=True)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel", viewonly=True)

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
    def get_one_object(idx):
        """
        Method to get one permission by its id

        :param int idx: ID of the permission
        :return: an instance of object :class:`PermissionViewRoleModel`
        :rtype: :class:`PermissionViewRoleModel`
        """
        return PermissionViewRoleModel.query.get(idx)

    def update(self, data):
        """
        Updates the object in the database and automatically updates the updated_at field
        :param dict data:  A dictionary containing the updated data for the execution
        """
        for key, item in data.items():
            setattr(self, key, item)
        super().update(data)

    @staticmethod
    def get_all_objects():
        return PermissionViewRoleModel.query.all()

    def __repr__(self):
        return "{} can {} on {}".format(self.role_id, self.action_id, self.api_view_id)


class PermissionsDAG(TraceAttributes):
    __tablename__ = "permission_dag"
    __table_args__ = (db.UniqueConstraint("dag_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    dag_id = db.Column(
        db.String(128), db.ForeignKey("deployed_dags.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel", viewonly=True)

    def __init__(self, data):
        super().__init__()
        self.dag_id = data.get("dag_id")
        self.user_id = data.get("user_id")

    def __repr__(self):
        return f"User {self.user_id} can access {self.dag_id}"

    @staticmethod
    def get_all_objects():
        return PermissionsDAG.query.all()

    @staticmethod
    def get_user_dag_permissions(user_id):
        return PermissionsDAG.query.filter_by(user_id=user_id).all()

    @staticmethod
    def add_all_permissions_to_user(user_id):
        dags = DeployedDAG.get_all_objects()
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user_id}) for dag in dags
        ]
        for permission in permissions:
            permission.save()

    @staticmethod
    def check_if_has_permissions(user_id, dag_id):
        permission = PermissionsDAG.query.filter_by(
            user_id=user_id, dag_id=dag_id
        ).first()
        if permission is None:
            return False
        return True
