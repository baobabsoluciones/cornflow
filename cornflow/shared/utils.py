"""

"""
import hashlib
import json

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


def hash_json_256(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
