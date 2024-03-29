"""
This file contains the model that has the actions that can be performed on an REST API endpoint
"""
from cornflow.models.meta_models import EmptyBaseModel
from cornflow.shared import db


class ActionModel(EmptyBaseModel):
    """
    Model to store the actions that can be performed over the REST API: get, patch, post, put, delete.
    This model inherits from :class:`EmptyBaseModel` and does not have traceability

    The fields for this model are:

    - **id**: an integer value to represent the action
    - **name**: a string to give meaning to the action ('get', 'patch', 'post', 'put', 'delete')
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
        return f"<Action {self.id}: {self.name}>"

    def __str__(self):
        return self.__repr__()
