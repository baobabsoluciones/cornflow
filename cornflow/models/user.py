# Imports from sqlalchemy
from sqlalchemy.sql import expression

# Imports from internal modules
from .meta_model import TraceAttributes
from .roles import UserRoleModel
from ..shared.utils import bcrypt, db


class UserModel(TraceAttributes):
    """
    Model class for the Users.
    It inherits from :class:`TraceAttributes` to have trace fields.

    The class :class:`UserModel` has the following fields:

    - **id**: int, the user id, primary key for the users.
    - **name**: str, the name of the user.
    - **email**: str, the email of the user.
    - **password**: str, the hashed password of the user.
    - **admin**: bool, if the user is an admin.
    - **super_admin**: bool, if the user is a super_admin.
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

    id = db.Column(db.Integer, primary_key=True)
    # TODO: should be first_name
    name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=True)
    # TODO: should be unique
    username = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    admin = db.Column(
        db.Boolean(), server_default=expression.false(), default=False, nullable=False
    )
    super_admin = db.Column(
        db.Boolean(), server_default=expression.false(), default=False, nullable=False
    )
    instances = db.relationship("InstanceModel", backref="users", lazy=True)
    # roles = db.relationship("RoleModel", secondary="UserRoleModel", backref="users")

    def __init__(self, data):

        super().__init__()
        self.name = data.get("name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        self.email = data.get("email")
        self.password = self.__generate_hash(data.get("password"))
        self.admin = False
        self.super_admin = False

    def update(self, data):
        """
        Updates the user information in the database

        :param dict data: the data to update the user
        """
        for key, item in data.items():
            if key == "password":
                new_password = self.__generate_hash(item)
                setattr(self, key, new_password)
            elif key == "admin" or key == "super_admin":
                continue
            else:
                setattr(self, key, item)

        super().update(data)
        db.session.commit()

    def disable(self):
        """
        Disables the user in the database
        """
        super().disable()

    def delete(self):
        """
        Deletes the user from the database
        """
        db.session.delete(self)
        db.session.commit()

    def is_admin(self):
        return UserRoleModel.is_admin(self.id)

    def is_super_admin(self):
        return UserRoleModel.is_super_admin(self.id)

    @staticmethod
    def __generate_hash(password):
        """
        Method to generate the hash from the password.

        :param str password: The password given by the user .
        :return: The hashed password.
        :rtype: str
        """
        return bcrypt.generate_password_hash(password, rounds=10).decode("utf8")

    def check_hash(self, password):
        """
        Method to check if the hash stored in the database is the same as the password given by the user

        :param str password: The password given by the user.
        :return: If the password is the same or not.
        :rtype: bool
        """
        return bcrypt.check_password_hash(self.password, password)

    @staticmethod
    def get_all_users():
        """
        Query to get all users

        :return: A list with all the users.
        :rtype: list(:class:`UserModel`)
        """
        return UserModel.query.filter_by(deleted_at=None)

    @staticmethod
    def get_one_user(idx):
        """
        Query to get the information of one user

        :param int idx: ID of the user
        :return: The user
        :rtype: :class:`UserModel`
        """
        return UserModel.query.filter_by(id=idx, deleted_at=None).first()

    @staticmethod
    def get_one_user_by_email(em):
        """
        Query to get one user from the email

        :param str em: User email
        :return: The user
        :rtype: :class:`UserModel`
        """
        return UserModel.query.filter_by(email=em, deleted_at=None).first()

    @staticmethod
    def get_one_user_by_username(username):
        """

        :param username:
        :type username:
        :return:
        :rtype:
        """
        return UserModel.query.filter_by(name=username, deleted_at=None).first()

    @staticmethod
    def get_user_info(idx):
        """
        Query to get the permission levels of a user

        :param int idx: The user id.
        :return: A tuple with the values of admin adn super_admin for the given user
        :rtype: tuple(bool, bool)
        """
        user = UserModel.query.filter_by(id=idx, deleted_at=None).first()
        return user.admin, user.super_admin

    def __repr__(self):
        """
        Representation method of the class

        :return: The representation of the class
        :rtype: str
        """
        return "<id {}>".format(self.id)
