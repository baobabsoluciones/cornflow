"""

"""
from abc import ABCMeta

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model, DefaultMeta
from sqlalchemy.ext.declarative import declarative_base


class CustomABCMeta(DefaultMeta, ABCMeta):
    pass


database = SQLAlchemy(
    model_class=declarative_base(cls=Model, metaclass=CustomABCMeta, name="Model")
)
password_crypt = Bcrypt()
