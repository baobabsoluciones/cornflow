""" """

from cornflow.models import ActionModel

from cornflow.shared import db


class ActionModel(ActionModel):
    """
    This model contains the base actions over the REST API. These are:
    * can get
    * can patch
    * can post
    * can put
    * can delete
    """

    __tablename__ = "actions"
    __table_args__ = {"extend_existing": True}

    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="actions",
        lazy=True,
        primaryjoin="and_(ActionModel.id==PermissionViewRoleModel.action_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
