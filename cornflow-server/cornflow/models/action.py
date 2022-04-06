"""

"""
from cornflow_core.models import ActionBaseModel

# from .meta_model import EmptyModel
from cornflow_core.shared import database as db


class ActionModel(ActionBaseModel):
    """
    This model contains the base actions over the REST API. These are:

    * can get
    * can patch
    * can post
    * can put
    * can delete
    """

    __tablename__ = "actions"

    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="actions",
        lazy=True,
        primaryjoin="and_(ActionModel.id==PermissionViewRoleModel.action_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
