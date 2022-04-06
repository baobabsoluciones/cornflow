"""
Models defined for the roles and the assignation of roles to users.
"""

from cornflow_core.models import TraceAttributesModel, RoleBaseModel

# Import from internal modules
from ..shared.const import ADMIN_ROLE, SERVICE_ROLE
from ..shared.utils import db


class RoleModel(RoleBaseModel):
    # TODO: Should have a user_id to store the user that defined the role?
    __tablename__ = "roles"

    user_roles = db.relationship(
        "UserRoleModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleModel.id==UserRoleModel.role_id, "
        "UserRoleModel.deleted_at==None)",
        cascade="all,delete",
    )
    permissions = db.relationship(
        "PermissionViewRoleModel",
        backref="roles",
        lazy=True,
        primaryjoin="and_(RoleModel.id==PermissionViewRoleModel.role_id, "
        "PermissionViewRoleModel.deleted_at==None)",
        cascade="all,delete",
    )


class UserRoleModel(TraceAttributesModel):
    # TODO: Should have a user_id to store the user that defined the assignation?
    __tablename__ = "user_role"
    __table_args__ = (db.UniqueConstraint("user_id", "role_id"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel", viewonly=True)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel", viewonly=True)

    def __init__(self, data):
        """
        Method to initialize th assignation of a role to a user that

        :param dict data: dict with the information needed to  create a new assignation of a role to a user
        """
        super().__init__()
        self.user_id = data.get("user_id")
        self.role_id = data.get("role_id")

    @classmethod
    def get_one_user(cls, user_id):
        """
        Method to get all the assigned roles to one user

        :param int user_id: the ID of the user
        :return: a list with all the objects of the assigned roles.
        :rtype: list
        """
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def del_one_user(cls, user_id):
        """
        Method to delete all the assigned roles to one user

        :param int user_id: the ID of the user
        :return: a list with all the deleted objects.
        :rtype: list
        """
        return cls.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    @classmethod
    def get_all_objects(cls):
        """
        Method to get all the role assignations to all the users

        :return: a list containing all the objects in the table
        :rtype: list
        """
        return cls.query.all()

    @classmethod
    def get_one_object(cls, idx):
        """
        Method to get one assignation of role by its id

        :param int idx: ID of the assignation
        :return: an instance of object :class:`UserRoleModel`
        :rtype: :class:`UserRoleModel`
        """
        return cls.query.get(idx)

    @classmethod
    def get_one_user_role(cls, user_id, role_id):
        """
        Method to get one object from the user and role

        :param int user_id: id of the specific user
        :param int role_id: id of the specific role
        :return: an instance of the user roles model
        :rtype: :class:`UserRoleModel`
        """
        return cls.query.filter_by(user_id=user_id, role_id=role_id).first()

    @staticmethod
    def is_admin(user_id):
        """
        Method that checks if a given user has the admin role assigned

        :param int user_id: the ID of the user
        :return: a boolean indicating if the user has the admin role assigned or not
        :rtype: boolean
        """
        user_roles = UserRoleModel.query.filter_by(user_id=user_id).all()
        for role in user_roles:
            if role.role_id == ADMIN_ROLE:
                return True

        return False

    @staticmethod
    def is_service_user(user_id):
        """
        Method that checks if a given user has the service role assigned

        :param int user_id: the ID of the user
        :return: a boolean indicating if the user has the service role assigned or not
        :rtype: boolean
        """
        user_roles = UserRoleModel.query.filter_by(user_id=user_id).all()
        for role in user_roles:
            if role.role_id == SERVICE_ROLE:
                return True

        return False

    @staticmethod
    def check_if_role_assigned(user_id, role_id):
        """
        Method to check if a user has a given role assigned

        :param int user_id: id of the specific user
        :param int role_id: id of the specific role
        :return: a boolean if the user has the role assigned
        :rtype: bool
        """
        user_role = UserRoleModel.get_one_user_role(user_id, role_id)
        return user_role is not None

    @staticmethod
    def check_if_role_assigned_disabled(user_id, role_id):
        """
        Method to check if a user has a given role assigned but disabled

        :param user_id: id of the specific user
        :param role_id: id of the specific role
        :return: a boolean if the user has the role assigned but disabled
        :rtype: bool
        """
        user_role = UserRoleModel.query.filter(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id,
            UserRoleModel.deleted_at != None,
        ).first()
        return user_role is not None

    def __repr__(self):
        """
        Method for the representation of the assigned roles

        :return: the representation
        :rtype: str
        """
        try:
            assignation = self.user.username + " has role " + self.role.name
            return assignation
        except AttributeError:
            assignation = str(self.user_id) + "has role" + str(self.role_id)
            return assignation

    def __str__(self):
        """
        Method for the string representation of the assigned roles

        :return: the string representation
        :rtype: str
        """
        try:
            assignation = self.user.username + " has role " + self.role.name
            return assignation
        except AttributeError:
            assignation = str(self.user_id) + " has role " + str(self.role_id)
            return assignation
