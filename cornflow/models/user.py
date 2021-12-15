# Imports from libraries
import re

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

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

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

    @property
    def roles(self):
        return {r.role.id: r.role.name for r in self.user_roles}

    def __init__(self, data):

        super().__init__()
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        self.password = self.__generate_hash(data.get("password"))
        self.email = data.get("email")

    def update(self, data):
        """
        Updates the user information in the database

        :param dict data: the data to update the user
        """
        # TODO: try not to use setattr
        for key, item in data.items():
            if key == "password":
                new_password = self.__generate_hash(item)
                setattr(self, key, new_password)
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
        """
        Returns a boolean if a user is an admin or not
        """
        return UserRoleModel.is_admin(self.id)

    def is_service_user(self):
        """
        Returns a boolean if a user is a super user or not
        """
        return UserRoleModel.is_service_user(self.id)

    def comes_from_ldap(self):
        """
        Returns a boolean if the user comes from ldap or not
        """
        return self.password is None

    @staticmethod
    def __generate_hash(password):
        """
        Method to generate the hash from the password.

        :param str password: the password given by the user .
        :return: the hashed password.
        :rtype: str
        """
        if password is None:
            return None
        return bcrypt.generate_password_hash(password, rounds=10).decode("utf8")

    def check_hash(self, password):
        """
        Method to check if the hash stored in the database is the same as the password given by the user

        :param str password: the password given by the user.
        :return: if the password is the same or not.
        :rtype: bool
        """
        return bcrypt.check_password_hash(self.password, password)

    @staticmethod
    def get_all_users():
        """
        Query to get all users

        :return: a list with all the users.
        :rtype: list(:class:`UserModel`)
        """
        return UserModel.query.filter_by(deleted_at=None)

    @staticmethod
    def get_one_user(idx):
        """
        Query to get the information of one user

        :param int idx: ID of the user
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return UserModel.query.filter_by(id=idx, deleted_at=None).first()

    @staticmethod
    def get_one_user_by_email(email):
        """
        Query to get one user from the email

        :param str email: User email
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return UserModel.query.filter_by(email=email, deleted_at=None).first()

    @staticmethod
    def get_one_user_by_username(username):
        """
        Returns one user (object) given a username
        :param str username: the user username that we are quering with
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return UserModel.query.filter_by(username=username, deleted_at=None).first()

    @staticmethod
    def check_username_in_use(username):
        """
        Checks if a username is already in use
        :param str username: the username to check
        :return: a boolean if the username is in use
        :rtype: bool
        """
        return UserModel.query.filter_by(username=username).first() is not None

    @staticmethod
    def check_email_in_use(email):
        """
        Checks if a email is already in use
        :param str email: the email to check
        :return: a boolean if the username is in use
        :rtype: bool
        """
        return UserModel.query.filter_by(email=email).first() is not None

    @staticmethod
    def check_password_pattern(password: str):
        """
        Checks if a password is valid
        :param password: the password to check
        :return: a dictionary containing: a boolean indicating if the password is valid, and a message
        :rtype: dict
        """
        if len(password) < 5:
            return {
                "valid": False,
                "message": "Password must contain at least 5. characters",
            }
        if password.islower() or password.isupper():
            return {
                "valid": False,
                "message": "Password must contain uppercase and lowercase letters",
            }
        if len(list(filter(str.isdigit, password))) == 0:
            return {
                "valid": False,
                "message": "Password must contain at least one number and one special character",
            }

        def is_special_character(character):
            return character in [
                char for char in "!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\"
            ]

        if len(list(filter(is_special_character, password))) == 0:
            return {
                "valid": False,
                "message": "Password must contain at least one number and one special character",
            }
        return {"valid": True, "message": ""}

    @staticmethod
    def check_email_pattern(email: str):
        """
        Checks if an email address is valid
        :param email: The email to validate
        :return: A dictionary containing: a boolean indicating if the email address is valid, and a message
        :rtype: dict
        """
        email_pattern = r"\b[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        if re.match(email_pattern, email) is None:
            return {"valid": False, "message": "Invalid email address"}
        return {"valid": True, "message": ""}

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)
