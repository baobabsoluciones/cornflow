from flask import current_app

from cornflow.models.dag import DeployedWorkflow
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.models.user import UserModel
from cornflow.models.user_role import UserRoleModel
from cornflow.shared import db
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE


class PermissionsDAG(TraceAttributesModel):
    __tablename__ = "permission_dag"
    __table_args__ = (db.UniqueConstraint("dag_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    dag_id = db.Column(
        db.String(128), db.ForeignKey("deployed_workflows.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel", viewonly=True)

    def __init__(self, data):
        super().__init__()
        self.dag_id = data.get("dag_id")
        self.user_id = data.get("user_id")

    def __repr__(self):
        return f"<DAG permission user: {self.user_id}, DAG: {self.dag_id}>"

    @classmethod
    def get_user_dag_permissions(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @staticmethod
    def add_all_permissions_to_user(user_id):
        dags = DeployedWorkflow.get_all_objects()
        permissions = [
            PermissionsDAG({"dag_id": dag.id, "user_id": user_id}) for dag in dags
        ]
        for permission in permissions:
            permission.save()

    @staticmethod
    def add_missing_dag_permissions(dag_ids, open_deployment=None) -> list:
        """
        Create and commit the permission_dag rows that are missing for the given DAGs.

        With open deployment (1) every active user gets access to every given DAG.
        Otherwise only users with the admin or the service role get access.
        Existing rows are never modified or duplicated.

        :param dag_ids: list of DAG ids (str)
        :param open_deployment: 1 for open deployment, 0 otherwise. If None, the value
            is read from current_app.config["OPEN_DEPLOYMENT"]. Strings are accepted.
        :return: the list of PermissionsDAG objects that have been created (empty if none)
        :raises Exception: any database error is re-raised after a session rollback
        """
        dag_ids = list(dict.fromkeys(dag_ids))
        if not dag_ids:
            return []

        if open_deployment is None:
            open_deployment = current_app.config["OPEN_DEPLOYMENT"]
        open_deployment = int(open_deployment)

        users = UserModel.get_all_users().all()
        if open_deployment != 1:
            privileged_ids = {
                user_id
                for (user_id,) in db.session.query(UserRoleModel.user_id)
                .filter(
                    UserRoleModel.role_id.in_([ADMIN_ROLE, SERVICE_ROLE]),
                    UserRoleModel.deleted_at.is_(None),
                )
                .distinct()
                .all()
            }
            users = [user for user in users if user.id in privileged_ids]
        if not users:
            return []

        existing = {
            (dag_id, user_id)
            for dag_id, user_id in db.session.query(
                PermissionsDAG.dag_id, PermissionsDAG.user_id
            )
            .filter(PermissionsDAG.dag_id.in_(dag_ids))
            .all()
        }

        new_permissions = [
            PermissionsDAG({"dag_id": dag_id, "user_id": user.id})
            for dag_id in dag_ids
            for user in users
            if (dag_id, user.id) not in existing
        ]
        if not new_permissions:
            return []

        try:
            db.session.add_all(new_permissions)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return new_permissions

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
