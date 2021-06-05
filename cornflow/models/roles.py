"""
Models defined for the roles and the assignation of roles to users.
"""

# Import from internal modules
from .meta_model import TraceAttributes
from ..shared.const import ADMIN_ROLE, SERVICE_ROLE
from ..shared.utils import db


class RoleModel(TraceAttributes):
    # TODO: Should have a user_id to store the user that defined the role?
    __tablename__ = "roles"

    id = db.Column(db.Integer, db.Sequence("roles_id_sq"), primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __init__(self, data):
        """
        Method to initialize an instance of a role

        :param dict data: dict with the information needed to the creation of a new role
        """
        super().__init__()
        self.id = data.get("id")
        self.name = data.get("name")

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
        """
        Gets all the objects on the table

        :return: a list with the objects defined
        :rtype: list
        """
        return RoleModel.query.all()

    @staticmethod
    def get_one_object(idx):
        """
        Gets one object defined on the table by its id

        :param int idx: the ID of the object
        :return: the object got from the database
        :rtype: :class:`RoleModel`
        """
        return RoleModel.query.get(idx)

    def __repr__(self):
        """
        Method for the representation of the roles

        :return: the representation of the role
        :rtype: str
        """
        return self.name

    def __str__(self):
        """
        Method for the string representation of the roles

        :return: the string rtepresentation of the roles
        :rtype: str
        """
        return self.name


class UserRoleModel(TraceAttributes):
    # TODO: Should have a user_id to store the user that defined the assignation?
    __tablename__ = "user_role"

    id = db.Column(db.Integer, db.Sequence("user_roles_id_sq"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("UserModel")

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("RoleModel")

    def __init__(self, data):
        """
        Method to initialize th assignation of a role to a user that

        :param dict data: dict with the information needed to  create a new assignation of a role to a user
        """
        super().__init__()
        self.user_id = data.get("user_id")
        self.role_id = data.get("role_id")

    @staticmethod
    def get_one_user(user_id):
        """
        Method to get all the assigned roles to one user

        :param int user_id: the ID of the user
        :return: a list with all the objects of the assigned roles.
        :rtype: list
        """
        return UserRoleModel.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_all_objects():
        """
        Method to get all the role assignations to all the users

        :return: a list containing all the objects in the table
        :rtype: list
        """
        return UserRoleModel.query.all()

    @staticmethod
    def get_one_object(idx):
        """
        Method to get one assignation of role by its id

        :param int idx: ID of the assignation
        :return: an instance of object :class:`UserRoleModel`
        :rtype: :class:`UserRoleModel`
        """
        return UserRoleModel.query.get(idx)

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

    def __repr__(self):
        """
        Method for the representation of the assigned roles

        :return: the representation
        :rtype: str
        """
        return self.user.name + " has role " + self.role.name

    def __str__(self):
        """
        Method for the string representation of the assigned roles

        :return: the string representation
        :rtype: str
        """
        return self.user.name + " has role " + self.role.name
