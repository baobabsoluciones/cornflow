"""
This file contains the PermissionViewRoleModel
"""
# Imports from external libraries
from typing import TYPE_CHECKING

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.models.dag import DeployedDAG
from cornflow.shared import db
if TYPE_CHECKING:
    from cornflow.models.action import ActionModel
    from cornflow.models.role import RoleModel
    from cornflow.models.view import ViewModel


class PermissionViewRoleModel(TraceAttributesModel):
    """
    This model has the permissions that can be defined between an action, a view and a role
    It inherits from :class:`TraceAttributesModel` to have trace fields

    The :class:`PermissionViewRoleModel` has the following fields:

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
    __table_args__ = (db.UniqueConstraint("action_id", "api_view_id", "role_id"), {"extend_existing": True})

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True, autoincrement=True)

    action_id: db.Mapped[int] = db.mapped_column(db.Integer, db.ForeignKey("actions.id"), nullable=False)
    action: db.Mapped["ActionModel"] = db.relationship("ActionModel", viewonly=True)

    api_view_id: db.Mapped[int] = db.mapped_column(db.Integer, db.ForeignKey("api_view.id"), nullable=False)
    api_view: db.Mapped["ViewModel"] = db.relationship("ViewModel", viewonly=True)

    role_id: db.Mapped[int] = db.mapped_column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role: db.Mapped["RoleModel"] = db.relationship("RoleModel", viewonly=True)

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


class PermissionsDAG(TraceAttributesModel):
    __tablename__ = "permission_dag"
    __table_args__ = (
        {"extend_existing": True},
        # db.UniqueConstraint("dag_id", "user_id"),
    )

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True, autoincrement=True)

    dag_id: db.Mapped[str] = db.mapped_column(
        db.String(128), db.ForeignKey("deployed_dags.id"), nullable=False
    )
    user_id: db.Mapped[int] = db.mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel", viewonly=True)

    def __init__(self, data):
        super().__init__()
        self.dag_id = data.get("dag_id")
        self.user_id = data.get("user_id")

    def __repr__(self):
        return f"<DAG permission user: {self.user_id}, DAG: {self.dag_id}<"

    @classmethod
    def get_user_dag_permissions(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @staticmethod
    def add_all_permissions_to_user(user_id):
        dags = DeployedDAG.get_all_objects()
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user_id}) for dag in dags
        ]
        for permission in permissions:
            permission.save()

    @staticmethod
    def delete_all_permissions_from_user(user_id):
        permissions = PermissionsDAG.get_user_dag_permissions(user_id)
        for perm in permissions:
            perm.delete()

    @staticmethod
    def check_if_has_permissions(user_id, dag_id):
        permission = PermissionsDAG.query.filter_by(
            user_id=user_id, dag_id=dag_id
        ).first()
        if permission is None:
            return False
        return True
