"""

"""
from cornflow_core.models import EmptyBaseModel

# from .meta_model import EmptyModel
from ..shared.utils import db


class ActionModel(EmptyBaseModel):
    """
    This model contains the base actions over the REST API. These are:

    * can get
    * can patch
    * can post
    * can put
    * can delete
    """

    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="actions",
        lazy=True,
        primaryjoin="and_(ActionModel.id==PermissionViewRoleModel.action_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )

    def __repr__(self):
        return str(self.id) + ": " + self.name

    @classmethod
    def get_all_objects(cls):
        return cls.query.all()

    @classmethod
    def get_one_object(cls, idx):
        return cls.query.get(idx)
