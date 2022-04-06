"""

"""
import re
import string
import random

from .meta_models import TraceAttributesModel
from cornflow_backend.shared import (
    password_crypt,
    database,
    check_password_pattern,
    check_email_pattern,
)
from cornflow_backend.exceptions import InvalidCredentials


class UserBaseModel(TraceAttributesModel):
    __abstract__ = True
    id = database.Column(database.Integer, primary_key=True)
    first_name = database.Column(database.String(128), nullable=True)
    last_name = database.Column(database.String(128), nullable=True)
    username = database.Column(database.String(128), nullable=False, unique=True)
    password = database.Column(database.String(128), nullable=True)
    email = database.Column(database.String(128), nullable=False, unique=True)

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
        # TODO: try not to use setattr
        for key, item in data.items():
            if key == "password":
                new_password = self.__generate_hash(item)
                setattr(self, key, new_password)
            else:
                setattr(self, key, item)

        super().update(data)

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
        return password_crypt.generate_password_hash(password, rounds=10).decode("utf8")

    def check_hash(self, password):
        """
        Method to check if the hash stored in the database is the same as the password given by the user

        :param str password: the password given by the user.
        :return: if the password is the same or not.
        :rtype: bool
        """
        return password_crypt.check_password_hash(self.password, password)

    @classmethod
    def get_all_users(cls):
        """
        Query to get all users

        :return: a list with all the users.
        :rtype: list(:class:`UserModel`)
        """
        return cls.query.filter_by(deleted_at=None)

    @classmethod
    def get_one_user(cls, idx):
        """
        Query to get the information of one user

        :param int idx: ID of the user
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.query.filter_by(id=idx, deleted_at=None).first()

    @classmethod
    def get_one_user_by_email(cls, email):
        """
        Query to get one user from the email

        :param str email: User email
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.query.filter_by(email=email, deleted_at=None).first()

    @classmethod
    def get_one_user_by_username(cls, username):
        """
        Returns one user (object) given a username
        :param str username: the user username that we are quering with
        :return: the user object
        :rtype: :class:`UserModel`
        """
        return cls.query.filter_by(username=username, deleted_at=None).first()

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
    def generate_random_password():
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

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)
