from cornflow_backend.models import UserBaseModel

# Imports from internal modules

from .roles import UserRoleModel
from ..shared.utils import db


class UserModel(UserBaseModel):
    """
    Model class for the Users.
    It inherits from :class:`TraceAttributes` to have trace fields.

    The class :class:`UserModel` has the following fields:

    - **id**: int, the user id, primary key for the users.
    - **first_name**: str, the name of the user.
    - **last_name**: str, the name of the user.
    - **username**: str, the username of the user used for the login.
    - **email**: str, the email of the user.
    - **password**: str, the hashed password of the user.
    - **created_at**: datetime, the datetime when the execution was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the execution was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the execution was deleted (in UTC). Even though it is deleted,
      actually, it is not deleted from the database, in order to have a command that cleans up deleted data
      after a certain time of its deletion.
      This datetime is generated automatically, the user does not need to provide it.

    :param dict data: the parsed json got from and endpoint that contains all the required information to
      create a new user.
    """

    __tablename__ = "users"

    instances = db.relationship(
        "InstanceModel",
        backref="users",
        lazy=True,
        primaryjoin="and_(UserModel.id==InstanceModel.user_id, "
        "InstanceModel.deleted_at==None)",
        cascade="all,delete",
    )

    cases = db.relationship(
        "CaseModel",
        backref="users",
        lazy=True,
        primaryjoin="and_(UserModel.id==CaseModel.user_id, CaseModel.deleted_at==None)",
        cascade="all,delete",
    )

    user_roles = db.relationship("UserRoleModel", cascade="all,delete", backref="users")

    dag_permissions = db.relationship(
        "PermissionsDAG",
        cascade="all,delete",
        backref="users",
        primaryjoin="and_(UserModel.id==PermissionsDAG.user_id)",
    )

    @property
    def roles(self):
        return {r.role.id: r.role.name for r in self.user_roles}

    def is_admin(self):
        """
        Returns a boolean if a user is an admin or not
        """
        return UserRoleModel.is_admin(self.id)

    def is_service_user(self):
        """
        Returns a boolean if a user is a super user or not
        """
        return UserRoleModel.is_service_user(self.id)

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)
