"""
This file contains the UserBaseModel
"""
import random
import string

from cornflow_core.exceptions import InvalidCredentials
from cornflow_core.shared import (
    bcrypt,
    db,
    check_password_pattern,
    check_email_pattern,
)
from .meta_models import TraceAttributesModel
from .user_role import UserRoleBaseModel


class UserBaseModel(TraceAttributesModel):
    """
    Model class for the Users
    It inherits from :class:`TraceAttributesModel` to have trace fields

    The :class:`UserBaseModel` has the following fields:

    - **id**: int, the primary key for the users, a integer value thar is auto incremented
    - **first_name**: str, to store the first name of the user. Usually is an optional field.
    - **last_name**: str, to store the last name of the user. Usually is and optional field.
    - **username**: str, the username of the user, used for the log in.
    - **password**: str, the hashed password stored on the database in the case that the authentication is done
      with auth db. In other authentication methods this field is empty
    - **email**: str, the email of the user, used to send emails in case of password recovery.
    - **created_at**: datetime, the datetime when the user was created (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **updated_at**: datetime, the datetime when the user was last updated (in UTC).
      This datetime is generated automatically, the user does not need to provide it.
    - **deleted_at**: datetime, the datetime when the user was deleted (in UTC).
      This field is used only if we deactivate instead of deleting the record.
      This datetime is generated automatically, the user does not need to provide it.
    """

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

    user_roles = db.relationship(
        "UserRoleBaseModel", cascade="all,delete", backref="users"
    )

    @property
    def roles(self):
        """
        This property gives back the roles assigned to the user
        """
        return {r.role.id: r.role.name for r in self.user_roles}

    def __init__(self, data):
        super().__init__()
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        # TODO: handle better None passwords that can be found when using ldap
        check_pass, msg = check_password_pattern(data.get("password"))
        if check_pass:
            self.password = self.__generate_hash(data.get("password"))
        else:
            raise InvalidCredentials(msg)

        check_email, msg = check_email_pattern(data.get("email"))
        if check_email:
            self.email = data.get("email")
        else:
            raise InvalidCredentials(msg)

    def update(self, data):
        """
        Updates the user information in the database

        :param dict data: the data to update the user
        """
        # First we create the hash of the new password and then we update the object
        new_password = data.get("password")
        if new_password:
            new_password = self.__generate_hash(new_password)
            data["password"] = new_password
        super().update(data)

    def comes_from_external_provider(self):
        """
        Returns a boolean if the user comes from an external_provider or not
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

    @classmethod
    def get_all_users(cls):
        """
        Query to get all users

        :return: a list with all the users.
        :rtype: list(:class:`UserModel`)
        """
        return cls.get_all_objects()

    @classmethod
    def get_one_user(cls, idx):
        """
        Query to get the information of one user

        :param int idx: ID of the user
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(idx=idx)

    @classmethod
    def get_one_user_by_email(cls, email):
        """
        Query to get one user from the email

        :param str email: User email
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(email=email)

    @classmethod
    def get_one_user_by_username(cls, username):
        """
        Returns one user (object) given a username

        :param str username: the user username that we want to query for
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.get_one_object(username=username)

    def check_username_in_use(self):
        """
        Checks if a username is already in use

        :return: a boolean if the username is in use
        :rtype: bool
        """
        return self.query.filter_by(username=self.username).first() is not None

    def check_email_in_use(self):
        """
        Checks if a email is already in use

        :return: a boolean if the username is in use
        :rtype: bool
        """
        return self.query.filter_by(email=self.email).first() is not None

    @staticmethod
    def generate_random_password() -> str:
        """
        Method to generate a new random password for the user

        :return: the newly generated password
        :rtype: str
        """
        nb_lower = random.randint(1, 9)
        nb_upper = random.randint(10 - nb_lower, 11)
        nb_numbers = random.randint(1, 3)
        nb_special_char = random.randint(1, 3)
        upper_letters = random.sample(string.ascii_uppercase, nb_upper)
        lower_letters = random.sample(string.ascii_lowercase, nb_lower)
        numbers = random.sample(list(map(str, list(range(10)))), nb_numbers)
        symbols = random.sample("!¡?¿#$%&'()*+-_./:;,<>=@[]^`{}|~\"\\", nb_special_char)
        chars = upper_letters + lower_letters + numbers + symbols
        random.shuffle(chars)
        pwd = "".join(chars)
        return pwd

    def is_admin(self) -> bool:
        """
        This should return True or False if the user is an admin

        :return: if the user is an admin or not
        :rtype: bool
        """
        return UserRoleBaseModel.is_admin(self.id)

    def is_service_user(self) -> bool:
        """
        This should return True or False if the user is a service user (type of user used for internal tasks)

        :return: if the user is a service_user or not
        :rtype: bool
        """
        return UserRoleBaseModel.is_service_user(self.id)

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)

    def __str__(self):
        return self.__repr__()
