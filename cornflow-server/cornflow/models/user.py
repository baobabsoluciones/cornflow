"""
This file contains the UserModel
"""

# Imports from external libraries
import random
import string
from datetime import datetime, timezone, timedelta

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.models.user_role import UserRoleModel
from cornflow.shared import (
    bcrypt,
    db,
)
from cornflow.shared.exceptions import InvalidCredentials
from cornflow.shared.validators import (
    check_password_pattern,
    check_email_pattern,
)


class UserModel(TraceAttributesModel):
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
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=True)
    pwd_last_change = db.Column(db.DateTime, nullable=True)
    email = db.Column(db.String(128), nullable=False, unique=True)

    user_roles = db.relationship("UserRoleModel", cascade="all,delete", backref="users")

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

    dag_permissions = db.relationship(
        "PermissionsDAG",
        cascade="all,delete",
        backref="users",
        primaryjoin="and_(UserModel.id==PermissionsDAG.user_id)",
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
        self.pwd_last_change = datetime.now(timezone.utc)
        # TODO: handle better None passwords that can be found when using ldap
        check_pass, msg = check_password_pattern(data.get("password"))
        if check_pass:
            self.password = self.__generate_hash(data.get("password"))
        else:
            raise InvalidCredentials(
                msg, log_txt="Error while trying to create a new user. " + msg
            )

        check_email, msg = check_email_pattern(data.get("email"))
        if check_email:
            self.email = data.get("email")
        else:
            raise InvalidCredentials(
                msg, log_txt="Error while trying to create a new user. " + msg
            )

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
            data["pwd_last_change"] = datetime.now(timezone.utc)
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

    def is_admin(self):
        """
        Returns a boolean if a user is an admin or not
        """
        return UserRoleModel.is_admin(self.id)

    def is_service_user(self):
        """
        Returns a boolean if a user is a service user or not
        """
        return UserRoleModel.is_service_user(self.id)

    def __repr__(self):
        """
        Representation method of the class

        :return: the representation of the class
        :rtype: str
        """
        return "<Username {}>".format(self.username)

    def __str__(self):
        return self.__repr__()
