"""
This file defines the database session with SQLAlchemy and the password encryption with Bcrypt
Additionally we add the option to have our database models inherit ABCMeta class so that abstract methods can be defined
"""
from abc import ABCMeta

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model, DefaultMeta
from sqlalchemy.ext.declarative import declarative_base


class CustomABCMeta(DefaultMeta, ABCMeta):
    """
    Custom meta class so that the models inherit ABCMeta
    """

    pass


db = SQLAlchemy(
    model_class=declarative_base(cls=Model, metaclass=CustomABCMeta, name="Model")
)
bcrypt = Bcrypt()
